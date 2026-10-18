import React, { useRef, useState } from 'react';
import {
  Animated,
  LayoutAnimation,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  UIManager,
  View,
} from 'react-native';
import { Colors } from '../theme/colors';

// Enable LayoutAnimation on Android
if (Platform.OS === 'android') {
  UIManager.setLayoutAnimationEnabledExperimental?.(true);
}

interface PlanPreviewProps {
  plan: Record<string, unknown> | null;
}

export function PlanPreview({ plan }: PlanPreviewProps) {
  const [expanded, setExpanded] = useState(false);

  if (!plan) return null;

  const toggle = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpanded((v) => !v);
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity onPress={toggle} style={styles.header} activeOpacity={0.7}>
        <Text style={styles.headerText}>📋 Edit Plan</Text>
        <Text style={styles.chevron}>{expanded ? '▲' : '▼'}</Text>
      </TouchableOpacity>
      {expanded && (
        <ScrollView style={styles.body} horizontal>
          <Text style={styles.json}>{JSON.stringify(plan, null, 2)}</Text>
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 14,
    backgroundColor: 'rgba(15,23,42,0.9)',
    overflow: 'hidden',
    marginTop: 12,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 14,
  },
  headerText: {
    color: Colors.text,
    fontWeight: '600',
    fontSize: 14,
  },
  chevron: {
    color: Colors.muted,
    fontSize: 12,
  },
  body: {
    maxHeight: 240,
    paddingHorizontal: 14,
    paddingBottom: 14,
  },
  json: {
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    fontSize: 12,
    color: Colors.muted,
    lineHeight: 18,
  },
});
