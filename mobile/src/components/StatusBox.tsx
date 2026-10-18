import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Colors } from '../theme/colors';

interface StatusBoxProps {
  message: string;
  variant?: 'info' | 'error' | 'success';
}

export function StatusBox({ message, variant = 'info' }: StatusBoxProps) {
  const borderColor =
    variant === 'error'
      ? Colors.danger
      : variant === 'success'
      ? Colors.success
      : Colors.border;

  const textColor =
    variant === 'error'
      ? Colors.danger
      : variant === 'success'
      ? Colors.success
      : Colors.muted;

  return (
    <View style={[styles.container, { borderColor }]}>
      <Text style={[styles.text, { color: textColor }]}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderRadius: 14,
    backgroundColor: 'rgba(15,23,42,0.9)',
    padding: 14,
    minHeight: 56,
    justifyContent: 'center',
  },
  text: {
    fontSize: 14,
    lineHeight: 20,
  },
});
