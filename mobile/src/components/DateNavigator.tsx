// DateNavigator - Date picker with previous/next navigation

import React from 'react';
import { View, StyleSheet, Pressable } from 'react-native';
import * as Haptics from 'expo-haptics';
import { Text } from './Text';
import { Colors, Spacing, BorderRadius } from '../constants/theme';

interface DateNavigatorProps {
  date: Date;
  onDateChange: (date: Date) => void;
}

export function DateNavigator({ date, onDateChange }: DateNavigatorProps) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const currentDate = new Date(date);
  currentDate.setHours(0, 0, 0, 0);

  const isToday = currentDate.getTime() === today.getTime();
  const isFuture = currentDate.getTime() > today.getTime();

  const goToPreviousDay = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    const newDate = new Date(date);
    newDate.setDate(newDate.getDate() - 1);
    onDateChange(newDate);
  };

  const goToNextDay = () => {
    if (!isToday && !isFuture) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      const newDate = new Date(date);
      newDate.setDate(newDate.getDate() + 1);
      onDateChange(newDate);
    }
  };

  const goToToday = () => {
    if (!isToday) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      onDateChange(new Date());
    }
  };

  const formatDate = (d: Date): string => {
    const options: Intl.DateTimeFormatOptions = {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
    };
    return d.toLocaleDateString('en-US', options);
  };

  const getDayLabel = (): string => {
    if (isToday) return 'Today';

    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (currentDate.getTime() === yesterday.getTime()) return 'Yesterday';

    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return days[currentDate.getDay()];
  };

  return (
    <View style={styles.container}>
      <Pressable
        onPress={goToPreviousDay}
        style={({ pressed }) => [styles.navButton, pressed && styles.navButtonPressed]}
      >
        <Text variant="h2" color="secondary">‹</Text>
      </Pressable>

      <Pressable onPress={goToToday} style={styles.dateInfo}>
        <View style={styles.dayRow}>
          <Text variant="h2" weight="bold">
            {getDayLabel()}
          </Text>
          {isToday && (
            <View style={styles.nowBadge}>
              <Text variant="caption" weight="semibold" style={styles.nowText}>
                NOW
              </Text>
            </View>
          )}
        </View>
        <Text variant="bodySmall" color="secondary">
          {formatDate(date)}
        </Text>
      </Pressable>

      <Pressable
        onPress={goToNextDay}
        style={({ pressed }) => [
          styles.navButton,
          pressed && styles.navButtonPressed,
          (isToday || isFuture) && styles.navButtonDisabled,
        ]}
        disabled={isToday || isFuture}
      >
        <Text variant="h2" color={isToday || isFuture ? 'muted' : 'secondary'}>
          ›
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },

  navButton: {
    width: 44,
    height: 44,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.backgroundCard,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.border,
  },

  navButtonPressed: {
    backgroundColor: Colors.backgroundElevated,
    transform: [{ scale: 0.95 }],
  },

  navButtonDisabled: {
    opacity: 0.3,
  },

  dateInfo: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
  },

  dayRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },

  nowBadge: {
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: BorderRadius.sm,
  },

  nowText: {
    color: Colors.text,
    fontSize: 10,
  },
});
