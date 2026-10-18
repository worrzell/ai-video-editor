import React, { useState, useEffect, useRef } from 'react';
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
  const [renderProgress, setRenderProgress] = useState<{
    step: number;
    total_steps: number;
    percent: number;
    step_name: string;
    message: string;
  } | null>(null);

  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const stopPolling = () => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  };

  const pollProgress = async () => {
    stopPolling();
    try {
      const prog = await apiRequest<{
        status: string;
        step: number;
        total_steps: number;
        percent: number;
        step_name: string;
        message: string;
      }>('/api/render/progress');
      if (prog && prog.status === 'processing') {
        setRendering(true);
        setRenderProgress(prog);
        setStatusMsg(prog.message);
        pollTimeoutRef.current = setTimeout(pollProgress, 30000);
      } else if (prog && prog.status === 'completed') {
        setRenderProgress({ ...prog, percent: 100, step_name: 'Complete' });
        setStatusMsg('Render complete! Go to Library tab to download.');
        setStatusVariant('success');
        setRendering(false);
      } else if (prog && prog.status === 'failed') {
        setRendering(false);
        setStatusMsg(`Render failed: ${prog.message || 'Error during rendering'}`);
        setStatusVariant('error');
      }
    } catch (e) {
      pollTimeoutRef.current = setTimeout(pollProgress, 30000);
    }
  };

  useEffect(() => {
    // Check if render is active when opening or switching to screen
    pollProgress();
    return () => {
      stopPolling();
    };
  }, []);

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
    setRenderProgress({
      step: 1,
      total_steps: 5,
      percent: 5,
      step_name: 'Ingesting Clips',
      message: 'Analyzing clips and generating timeline…',
    });
    setStatusMsg(
      `Generating edit plan with Gemini & rendering video${useResolve ? ' with DaVinci Resolve' : ''}…`
    );
    setStatusVariant('info');

    // Trigger initial check after 3s, then repeat every 30s
    stopPolling();
    pollTimeoutRef.current = setTimeout(pollProgress, 3000);

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

      stopPolling();
      setRenderProgress((prev) => (prev ? { ...prev, percent: 100, step_name: 'Complete' } : null));
      setStatusMsg('Render complete! Go to Library tab to download.');
      setStatusVariant('success');
      setPlan(res.plan);
      // Navigate to Library tab (index 2) after a short delay
      setTimeout(() => (navigation as any).navigate('Library'), 1500);
    } catch (e: unknown) {
      stopPolling();
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

          {rendering && renderProgress && (
            <View style={styles.progressContainer}>
              <View style={styles.progressHeader}>
                <Text style={styles.progressStepText}>
                  Step {renderProgress.step}/5: {renderProgress.step_name}
                </Text>
                <Text style={styles.progressPercentText}>{renderProgress.percent}%</Text>
              </View>
              <View style={styles.progressBarBg}>
                <View
                  style={[
                    styles.progressBarFill,
                    { width: `${Math.max(5, renderProgress.percent)}%` as any },
                  ]}
                />
              </View>
            </View>
          )}

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
  progressContainer: {
    padding: 12,
    borderRadius: 12,
    backgroundColor: 'rgba(15,23,42,0.7)',
    borderWidth: 1,
    borderColor: Colors.border,
    gap: 8,
  },
  progressHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  progressStepText: {
    color: Colors.text,
    fontSize: 13,
    fontWeight: '600',
    flex: 1,
  },
  progressPercentText: {
    color: Colors.primary,
    fontSize: 13,
    fontWeight: '700',
    marginLeft: 8,
  },
  progressBarBg: {
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(148,163,184,0.15)',
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 4,
    backgroundColor: Colors.primary,
  },
});
