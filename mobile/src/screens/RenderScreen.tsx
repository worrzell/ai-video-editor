import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { apiRequest } from '../api/client';
import { PlanPreview } from '../components/PlanPreview';
import { StatusBox } from '../components/StatusBox';
import { useAuthStore } from '../store/authStore';
import { Colors } from '../theme/colors';

export default function RenderScreen() {
  const { user } = useAuthStore();
  const navigation = useNavigation();
  const [prompt, setPrompt] = useState('');
  const [useResolve, setUseResolve] = useState(false);
  const [rendering, setRendering] = useState(false);
  const [statusMsg, setStatusMsg] = useState('Enter a prompt and render the final video.');
  const [statusVariant, setStatusVariant] = useState<'info' | 'error' | 'success'>('info');
  const [plan, setPlan] = useState<Record<string, unknown> | null>(null);

  const handleRender = async () => {
    if (!user) {
      Alert.alert('Sign In Required', 'Go to the Profile tab to sign in before rendering.');
      return;
    }
    if (!prompt.trim()) {
      setStatusMsg('Enter an edit prompt before rendering.');
      setStatusVariant('error');
      return;
    }

    setRendering(true);
    setPlan(null);
    setStatusMsg(
      `Generating edit plan with Gemini & rendering video${useResolve ? ' with DaVinci Resolve' : ''}…`
    );
    setStatusVariant('info');

    try {
      const body = new URLSearchParams({
        prompt: prompt.trim(),
        use_resolve: String(useResolve),
      }).toString();

      const res = await apiRequest<{ status: string; plan: Record<string, unknown> }>(
        '/api/render',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body,
        }
      );

      setStatusMsg('Render complete! Go to Library tab to download.');
      setStatusVariant('success');
      setPlan(res.plan);
      // Navigate to Library tab (index 2) after a short delay
      setTimeout(() => (navigation as any).navigate('Library'), 1500);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Render failed';
      setStatusMsg(`Render failed: ${msg}`);
      setStatusVariant('error');
    } finally {
      setRendering(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.content}>
        {!user && (
          <View style={styles.authBanner}>
            <Text style={styles.authBannerText}>
              👤 Sign in via the Profile tab to generate and render.
            </Text>
          </View>
        )}

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Generate & Render</Text>

          <Text style={styles.label}>Edit Prompt</Text>
          <TextInput
            style={styles.textArea}
            value={prompt}
            onChangeText={setPrompt}
            multiline
            numberOfLines={4}
            placeholder="e.g. create a fast-paced highlight reel with dynamic cuts"
            placeholderTextColor={Colors.muted}
          />

          <View style={styles.toggleRow}>
            <Text style={styles.toggleLabel}>Use DaVinci Resolve</Text>
            <Switch
              value={useResolve}
              onValueChange={setUseResolve}
              trackColor={{ false: Colors.border, true: Colors.primaryDark }}
              thumbColor={useResolve ? Colors.primary : Colors.muted}
            />
          </View>

          <TouchableOpacity
            style={[
              styles.primaryButton,
              (!user || rendering || !prompt.trim()) && styles.buttonDisabled,
            ]}
            onPress={handleRender}
            disabled={!user || rendering || !prompt.trim()}
          >
            {rendering ? (
              <View style={styles.loadingRow}>
                <ActivityIndicator color="#020617" size="small" />
                <Text style={styles.primaryButtonText}>Rendering…</Text>
              </View>
            ) : (
              <Text style={styles.primaryButtonText}>✨ Generate with Gemini & Render</Text>
            )}
          </TouchableOpacity>

          <StatusBox message={statusMsg} variant={statusVariant} />
        </View>

        <PlanPreview plan={plan} />
      </ScrollView>
    </KeyboardAvoidingView>
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
    gap: 14,
  },
  sectionTitle: { color: Colors.text, fontSize: 18, fontWeight: '700' },
  label: { color: Colors.text, fontWeight: '600', fontSize: 14 },
  textArea: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 12,
    backgroundColor: '#0b1222',
    color: Colors.text,
    padding: 12,
    fontSize: 14,
    minHeight: 100,
    textAlignVertical: 'top',
  },
  toggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 12,
    backgroundColor: 'rgba(15,23,42,0.5)',
    padding: 12,
  },
  toggleLabel: { color: Colors.text, fontSize: 14, fontWeight: '500', flex: 1 },
  primaryButton: {
    backgroundColor: Colors.primary,
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
  },
  primaryButtonText: { color: '#020617', fontWeight: '700', fontSize: 15 },
  buttonDisabled: { opacity: 0.45 },
  loadingRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
});
