import React, { useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { apiRequest } from '../api/client';
import { useAuthStore } from '../store/authStore';
import { Colors } from '../theme/colors';

export default function ProfileScreen() {
  const { user, login, logout } = useAuthStore();
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!username.trim() || !password) return;
    setError('');
    setLoading(true);
    try {
      const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';
      const res = await apiRequest<{ token: string; user: { id: string; username: string; role: string } }>(
        endpoint,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username: username.trim(), password }),
        }
      );
      await login(res.user, res.token);
      setUsername('');
      setPassword('');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await apiRequest('/api/auth/logout', { method: 'POST' });
    } catch {
      // Ignore server-side logout errors — clear local token regardless
    }
    await logout();
  };

  if (user) {
    return (
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        <View style={styles.card}>
          <View style={styles.userBadge}>
            <Text style={styles.userBadgeText}>👤 {user.username}</Text>
            <View style={styles.rolePill}>
              <Text style={styles.roleText}>{user.role}</Text>
            </View>
          </View>
          <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
            <Text style={styles.logoutButtonText}>Log Out</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Server Info</Text>
          <InfoRow label="API URL" value={process.env.EXPO_PUBLIC_API_BASE_URL ?? 'localhost:8000'} />
        </View>
      </ScrollView>
    );
  }

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      style={styles.container}
    >
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>
            {isRegister ? 'Create Account' : 'Sign In'}
          </Text>

          {!!error && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          <Text style={styles.label}>Username</Text>
          <TextInput
            style={styles.input}
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="e.g. admin"
            placeholderTextColor={Colors.muted}
          />

          <Text style={styles.label}>Password</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholder="Enter your password"
            placeholderTextColor={Colors.muted}
          />

          <TouchableOpacity
            style={[styles.primaryButton, loading && styles.buttonDisabled]}
            onPress={handleSubmit}
            disabled={loading}
          >
            <Text style={styles.primaryButtonText}>
              {loading ? 'Please wait…' : isRegister ? 'Register' : 'Sign In'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={() => { setIsRegister((v) => !v); setError(''); }}>
            <Text style={styles.switchText}>
              {isRegister
                ? 'Already have an account? Sign In'
                : "Don't have an account? Create one"}
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.bg },
  content: { padding: 16, gap: 16 },
  card: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 20,
    backgroundColor: Colors.surface,
    padding: 20,
    gap: 12,
  },
  sectionTitle: {
    color: Colors.text,
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 4,
  },
  label: { color: Colors.text, fontWeight: '600', fontSize: 14 },
  input: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 12,
    backgroundColor: '#0b1222',
    color: Colors.text,
    padding: 12,
    fontSize: 15,
  },
  primaryButton: {
    backgroundColor: Colors.primary,
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    marginTop: 4,
  },
  primaryButtonText: { color: '#020617', fontWeight: '700', fontSize: 15 },
  buttonDisabled: { opacity: 0.5 },
  switchText: { color: Colors.primary, fontSize: 13, textAlign: 'center', marginTop: 4 },
  errorBox: {
    backgroundColor: 'rgba(248,113,113,0.15)',
    borderWidth: 1,
    borderColor: Colors.danger,
    borderRadius: 10,
    padding: 10,
  },
  errorText: { color: Colors.danger, fontSize: 13 },
  userBadge: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  userBadgeText: { color: Colors.primary, fontWeight: '700', fontSize: 16, flex: 1 },
  rolePill: {
    backgroundColor: 'rgba(56,189,248,0.15)',
    borderWidth: 1,
    borderColor: 'rgba(56,189,248,0.3)',
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  roleText: { color: Colors.primary, fontSize: 12, fontWeight: '600' },
  logoutButton: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 12,
    padding: 12,
    alignItems: 'center',
    marginTop: 4,
  },
  logoutButtonText: { color: Colors.danger, fontWeight: '600' },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  infoLabel: { color: Colors.muted, fontSize: 13 },
  infoValue: { color: Colors.text, fontSize: 13, fontWeight: '500', flex: 1, textAlign: 'right' },
});
