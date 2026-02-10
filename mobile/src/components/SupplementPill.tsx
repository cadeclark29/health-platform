// SupplementPill - Tappable pill for logging supplements with spring animation

import React, { useRef, useEffect } from 'react';
import { Pressable, StyleSheet, View, Animated } from 'react-native';
import * as Haptics from 'expo-haptics';
import { Text } from './Text';
import { Colors, Spacing, BorderRadius } from '../constants/theme';

interface SupplementPillProps {
  name: string;
  dose?: string;
  isTaken: boolean;
  onPress: () => void;
  onLongPress?: () => void;
}

export function SupplementPill({
  name,
  dose,
  isTaken,
  onPress,
  onLongPress,
}: SupplementPillProps) {
  const scaleAnim = useRef(new Animated.Value(1)).current;
  const isFirstRender = useRef(true);

  // Spring animation when isTaken changes
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    Animated.sequence([
      Animated.spring(scaleAnim, {
        toValue: 1.05,
        friction: 3,
        tension: 200,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 4,
        tension: 100,
        useNativeDriver: true,
      }),
    ]).start();
  }, [isTaken]);

  const handlePress = () => {
    Haptics.impactAsync(
      isTaken
        ? Haptics.ImpactFeedbackStyle.Light
        : Haptics.ImpactFeedbackStyle.Medium
    );
    onPress();
  };

  const handleLongPress = () => {
    if (onLongPress) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
      onLongPress();
    }
  };

  return (
    <Animated.View style={{ transform: [{ scale: scaleAnim }] }}>
      <Pressable
        onPress={handlePress}
        onLongPress={handleLongPress}
        style={({ pressed }) => [
          styles.pill,
          isTaken && styles.pillTaken,
          pressed && styles.pillPressed,
        ]}
      >
        <View style={[styles.checkCircle, isTaken && styles.checkCircleTaken]}>
          {isTaken && <Text style={styles.checkMark}>✓</Text>}
        </View>
        <View style={styles.content}>
          <Text
            variant="bodySmall"
            weight="medium"
            style={isTaken ? styles.nameTaken : undefined}
            numberOfLines={1}
          >
            {name}
          </Text>
          <Text
            variant="caption"
            color="muted"
            style={isTaken ? styles.doseTaken : undefined}
          >
            {dose || 'Tap to set dose'}
          </Text>
        </View>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.backgroundElevated,
    borderRadius: BorderRadius.full,
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.sm,
  },

  pillTaken: {
    backgroundColor: Colors.successLight,
    borderColor: Colors.success,
  },

  pillPressed: {
    opacity: 0.8,
  },

  checkCircle: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: Colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },

  checkCircleTaken: {
    backgroundColor: Colors.success,
    borderColor: Colors.success,
  },

  checkMark: {
    color: Colors.textInverse,
    fontSize: 12,
    fontWeight: 'bold',
  },

  content: {
    flex: 1,
  },

  nameTaken: {
    color: Colors.success,
  },

  doseTaken: {
    color: Colors.success,
    opacity: 0.8,
  },
});
