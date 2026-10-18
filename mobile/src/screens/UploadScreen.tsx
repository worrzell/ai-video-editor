import * as ImagePicker from 'expo-image-picker';
import React, { useState } from 'react';
import {
  Alert,
  FlatList,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { BASE_URL, apiRequest, getToken } from '../api/client';
import { StatusBox } from '../components/StatusBox';
import { useStatus } from '../hooks/useStatus';
import { useAuthStore } from '../store/authStore';
import { Colors } from '../theme/colors';

export default function UploadScreen() {
  const { user } = useAuthStore();
  const { data: status, loading, refresh } = useStatus();
  const [uploadStatus, setUploadStatus] = useState('No uploads yet.');
  const [uploading, setUploading] = useState(false);

  const pickAndUpload = async () => {
    if (!user) {
      Alert.alert('Sign In Required', 'Go to the Profile tab to sign in before uploading.');
      return;
    }

    const { status: permStatus } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (permStatus !== 'granted') {
      Alert.alert('Permission Denied', 'Camera roll permission is required to pick videos.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Videos,
      allowsMultipleSelection: true,
      quality: 1,
    });

    if (result.canceled || result.assets.length === 0) return;

    setUploading(true);
    setUploadStatus(`Uploading ${result.assets.length} clip(s)…`);

    try {
      const formData = new FormData();
      for (const asset of result.assets) {
        const filename = asset.fileName ?? asset.uri.split('/').pop() ?? 'video.mp4';
        formData.append('files', {
          uri: asset.uri,
          name: filename,
          type: asset.mimeType ?? 'video/mp4',
        } as unknown as Blob);
      }

      const res = await apiRequest<{ message: string; uploaded: string[] }>('/api/upload', {
        method: 'POST',
        body: formData,
      });

      setUploadStatus(res.message ?? `Uploaded ${res.uploaded.length} file(s).`);
      await refresh();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Upload failed';
      setUploadStatus(`Upload failed: ${msg}`);
    } finally {
      setUploading(false);
    }
  };

  const clips = status?.clips ?? [];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={refresh} tintColor={Colors.primary} />}
    >
      {!user && (
        <View style={styles.authBanner}>
          <Text style={styles.authBannerText}>
            👤 Sign in via the Profile tab to upload clips.
          </Text>
        </View>
      )}

      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.sectionTitle}>Upload Clips</Text>
          {clips.length > 0 && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{clips.length}</Text>
            </View>
          )}
        </View>

        <TouchableOpacity
          style={[styles.primaryButton, (!user || uploading) && styles.buttonDisabled]}
          onPress={pickAndUpload}
          disabled={!user || uploading}
        >
          <Text style={styles.primaryButtonText}>
            {uploading ? 'Uploading…' : '🎬 Choose Videos'}
          </Text>
        </TouchableOpacity>

        <StatusBox
          message={uploadStatus}
          variant={uploadStatus.includes('failed') ? 'error' : 'info'}
        />
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Uploaded Clips</Text>
        {clips.length === 0 ? (
          <Text style={styles.emptyText}>No clips uploaded yet.</Text>
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
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  content: { padding: 16, gap: 16, paddingBottom: 32 },
  authBanner: {
    borderWidth: 1,
    borderColor: 'rgba(56,189,248,0.3)',
    borderRadius: 14,
    backgroundColor: 'rgba(56,189,248,0.08)',
    padding: 14,
  },
  authBannerText: { color: Colors.primary, fontSize: 14, textAlign: 'center' },
  card: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 20,
    backgroundColor: Colors.surface,
    padding: 20,
    gap: 12,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  sectionTitle: { color: Colors.text, fontSize: 18, fontWeight: '700', flex: 1 },
  badge: {
    backgroundColor: Colors.primary,
    borderRadius: 10,
    minWidth: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  badgeText: { color: '#020617', fontSize: 12, fontWeight: '700' },
  primaryButton: {
    backgroundColor: Colors.primary,
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
  },
  primaryButtonText: { color: '#020617', fontWeight: '700', fontSize: 15 },
  buttonDisabled: { opacity: 0.45 },
  emptyText: { color: Colors.muted, fontSize: 14 },
  clipRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 6 },
  clipIcon: { fontSize: 18 },
  clipName: { color: Colors.text, fontSize: 14, flex: 1 },
  separator: { height: 1, backgroundColor: Colors.border },
});
