import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { BASE_URL, getToken } from '../api/client';
import { StatusBox } from '../components/StatusBox';
import { useStatus } from '../hooks/useStatus';
import { useAuthStore } from '../store/authStore';
import { Colors } from '../theme/colors';

export default function LibraryScreen() {
  const { user } = useAuthStore();
  const { data: status, loading, refresh } = useStatus();
  const [downloading, setDownloading] = useState(false);
  const [downloadMsg, setDownloadMsg] = useState('');

  const handleDownload = async () => {
    if (!user) {
      Alert.alert('Sign In Required', 'Go to the Profile tab to sign in.');
      return;
    }
    setDownloading(true);
    setDownloadMsg('Downloading final video…');
    try {
      const token = await getToken();
      const destUri = FileSystem.cacheDirectory + 'final.mp4';

      const { status: dlStatus } = await FileSystem.downloadAsync(
        `${BASE_URL}/api/download/output`,
        destUri,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} }
      );

      if (dlStatus !== 200) {
        throw new Error(`Download failed with status ${dlStatus}`);
      }

      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(destUri, { mimeType: 'video/mp4', dialogTitle: 'Share Final Video' });
        setDownloadMsg('Video shared successfully.');
      } else {
        setDownloadMsg(`Video saved to cache: ${destUri}`);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Download failed';
      setDownloadMsg(`Failed: ${msg}`);
    } finally {
      setDownloading(false);
    }
  };

  const clips = status?.clips ?? [];
  const outputReady = status?.output_exists ?? false;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={loading} onRefresh={refresh} tintColor={Colors.primary} />
      }
    >
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>📁 Uploaded Clips</Text>
        {clips.length === 0 ? (
          <Text style={styles.emptyText}>
            No clips yet. Upload clips from the Upload tab.
          </Text>
        ) : (
          <FlatList
            data={clips}
            keyExtractor={(item) => item}
            scrollEnabled={false}
            renderItem={({ item }) => (
              <View style={styles.clipRow}>
                <Text style={styles.clipIcon}>🎬</Text>
                <Text style={styles.clipName} numberOfLines={1}>{item}</Text>
              </View>
            )}
            ItemSeparatorComponent={() => <View style={styles.separator} />}
          />
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>🎬 Final Output</Text>

        <View style={[styles.outputStatus, { borderColor: outputReady ? Colors.success : Colors.border }]}>
          <Text style={[styles.outputStatusText, { color: outputReady ? Colors.success : Colors.muted }]}>
            {outputReady ? '✅ Ready to download' : '⏳ No output yet — render from the Render tab'}
          </Text>
        </View>

        <TouchableOpacity
          style={[
            styles.downloadButton,
            (!outputReady || downloading || !user) && styles.buttonDisabled,
          ]}
          onPress={handleDownload}
          disabled={!outputReady || downloading || !user}
        >
          {downloading ? (
            <View style={styles.loadingRow}>
              <ActivityIndicator color={Colors.text} size="small" />
              <Text style={styles.downloadButtonText}>Downloading…</Text>
            </View>
          ) : (
            <Text style={styles.downloadButtonText}>⬇️ Download & Share</Text>
          )}
        </TouchableOpacity>

        {!!downloadMsg && (
          <StatusBox
            message={downloadMsg}
            variant={downloadMsg.includes('Failed') ? 'error' : 'success'}
          />
        )}

        <Text style={styles.hint}>Pull down to refresh status.</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  content: { padding: 16, gap: 16, paddingBottom: 32 },
  card: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 20,
    backgroundColor: Colors.surface,
    padding: 20,
    gap: 12,
  },
  sectionTitle: { color: Colors.text, fontSize: 18, fontWeight: '700' },
  emptyText: { color: Colors.muted, fontSize: 14 },
  clipRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 6 },
  clipIcon: { fontSize: 18 },
  clipName: { color: Colors.text, fontSize: 14, flex: 1 },
  separator: { height: 1, backgroundColor: Colors.border },
  outputStatus: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    backgroundColor: 'rgba(15,23,42,0.6)',
  },
  outputStatusText: { fontSize: 14, fontWeight: '500' },
  downloadButton: {
    borderWidth: 1,
    borderColor: Colors.primary,
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    backgroundColor: 'rgba(56,189,248,0.1)',
  },
  downloadButtonText: { color: Colors.primary, fontWeight: '700', fontSize: 15 },
  buttonDisabled: { opacity: 0.4 },
  loadingRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  hint: { color: Colors.muted, fontSize: 12, textAlign: 'center' },
});
