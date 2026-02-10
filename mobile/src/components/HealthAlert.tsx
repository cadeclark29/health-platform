// HealthAlert - Smart health recommendation cards for dashboard

import React from 'react';
import { View, StyleSheet, Pressable } from 'react-native';
import * as Haptics from 'expo-haptics';
import { Text, Card } from './index';
import { Colors, Spacing, BorderRadius } from '../constants/theme';
import { HealthAlert as HealthAlertType, HealthAlertAction } from '../types';

interface HealthAlertProps {
  alert: HealthAlertType;
  onActionPress?: (action: HealthAlertAction) => void;
}

export function HealthAlertCard({ alert, onActionPress }: HealthAlertProps) {
  const handleAction = (action: HealthAlertAction) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onActionPress?.(action);
  };

  return (
    <Card style={[styles.alertCard, { borderLeftColor: alert.color, borderLeftWidth: 3 }]}>
      <View style={styles.alertHeader}>
        <Text style={styles.alertIcon}>{alert.icon}</Text>
        <View style={styles.alertContent}>
          <View style={styles.alertTitleRow}>
            <Text variant="body" weight="semibold">{alert.title}</Text>
            {alert.severity === 'critical' && (
              <View style={styles.criticalBadge}>
                <Text variant="caption" style={styles.criticalText}>!</Text>
              </View>
            )}
          </View>
          <Text variant="bodySmall" color="secondary" style={styles.alertDesc}>
            {alert.description}
          </Text>
        </View>
      </View>

      {alert.actions.length > 0 && (
        <View style={styles.actionsRow}>
          {alert.actions.map((action, i) => {
            const actionColor = action.type === 'add' ? Colors.success
              : action.type === 'hold' ? Colors.warning
              : Colors.error;
            const actionBg = action.type === 'add' ? Colors.successLight
              : action.type === 'hold' ? Colors.warningLight
              : Colors.errorLight;

            return (
              <Pressable
                key={i}
                style={[styles.actionPill, { backgroundColor: actionBg }]}
                onPress={() => handleAction(action)}
              >
                <Text variant="caption" weight="semibold" style={{ color: actionColor }}>
                  {action.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  alertCard: {
    marginBottom: Spacing.sm,
  },
  alertHeader: {
    flexDirection: 'row',
    gap: Spacing.md,
  },
  alertIcon: {
    fontSize: 24,
    marginTop: 2,
  },
  alertContent: {
    flex: 1,
  },
  alertTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    marginBottom: Spacing.xs,
  },
  alertDesc: {
    lineHeight: 18,
  },
  criticalBadge: {
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: Colors.error,
    justifyContent: 'center',
    alignItems: 'center',
  },
  criticalText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
  actionsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
    marginTop: Spacing.md,
    paddingLeft: 36,
  },
  actionPill: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
  },
});
