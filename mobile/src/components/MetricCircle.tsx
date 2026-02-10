// MetricCircle - Circular progress indicator for health metrics

import React from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { Text } from './Text';
import { Colors, Spacing } from '../constants/theme';

interface MetricCircleProps {
  value: number | null | undefined;
  label: string;
  color: string;
  size?: 'sm' | 'md' | 'lg';
  maxValue?: number;
}

const sizeConfig = {
  sm: { diameter: 64, strokeWidth: 4, fontSize: 'lg' as const },
  md: { diameter: 80, strokeWidth: 5, fontSize: 'xl' as const },
  lg: { diameter: 100, strokeWidth: 6, fontSize: 'xxl' as const },
};

export function MetricCircle({
  value,
  label,
  color,
  size = 'md',
  maxValue = 100,
}: MetricCircleProps) {
  const config = sizeConfig[size];
  const radius = (config.diameter - config.strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const progress = value != null ? Math.min(value / maxValue, 1) : 0;
  const strokeDashoffset = circumference - progress * circumference;

  const getScoreColor = (score: number | null | undefined): string => {
    if (score == null) return Colors.textMuted;
    if (score >= 85) return Colors.success;
    if (score >= 70) return color;
    if (score >= 50) return Colors.warning;
    return Colors.error;
  };

  return (
    <View style={styles.container}>
      <View style={[styles.circleContainer, { width: config.diameter, height: config.diameter }]}>
        <Svg width={config.diameter} height={config.diameter}>
          {/* Background circle */}
          <Circle
            cx={config.diameter / 2}
            cy={config.diameter / 2}
            r={radius}
            stroke={Colors.border}
            strokeWidth={config.strokeWidth}
            fill="transparent"
          />
          {/* Progress circle */}
          {value != null && (
            <Circle
              cx={config.diameter / 2}
              cy={config.diameter / 2}
              r={radius}
              stroke={getScoreColor(value)}
              strokeWidth={config.strokeWidth}
              fill="transparent"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              transform={`rotate(-90 ${config.diameter / 2} ${config.diameter / 2})`}
            />
          )}
        </Svg>
        <View style={styles.valueContainer}>
          <Text
            variant={config.fontSize}
            weight="bold"
            style={{ color: getScoreColor(value) }}
          >
            {value != null ? Math.round(value) : '--'}
          </Text>
        </View>
      </View>
      <Text variant="caption" color="secondary" style={styles.label}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  circleContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  valueContainer: {
    position: 'absolute',
    justifyContent: 'center',
    alignItems: 'center',
  },
  label: {
    marginTop: Spacing.xs,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
});
