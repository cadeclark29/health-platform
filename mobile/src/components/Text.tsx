// Custom Text component with typography presets

import React from 'react';
import { Text as RNText, TextStyle, StyleSheet } from 'react-native';
import { Colors, Typography } from '../constants/theme';

type TextVariant =
  | 'display'
  | 'h1'
  | 'h2'
  | 'h3'
  | 'lg'
  | 'xl'
  | 'xxl'
  | 'body'
  | 'bodySmall'
  | 'caption'
  | 'label';

type TextColor = 'primary' | 'secondary' | 'muted' | 'success' | 'warning' | 'error' | 'inverse';

interface TextProps {
  children: React.ReactNode;
  variant?: TextVariant;
  color?: TextColor;
  weight?: keyof typeof Typography.weights;
  align?: 'left' | 'center' | 'right';
  style?: TextStyle | TextStyle[];
  numberOfLines?: number;
}

const variantStyles: Record<TextVariant, TextStyle> = {
  display: {
    fontSize: Typography.sizes.display,
    fontWeight: Typography.weights.bold,
    lineHeight: Typography.sizes.display * Typography.lineHeights.tight,
  },
  h1: {
    fontSize: Typography.sizes.xxxl,
    fontWeight: Typography.weights.bold,
    lineHeight: Typography.sizes.xxxl * Typography.lineHeights.tight,
  },
  h2: {
    fontSize: Typography.sizes.xxl,
    fontWeight: Typography.weights.semibold,
    lineHeight: Typography.sizes.xxl * Typography.lineHeights.tight,
  },
  h3: {
    fontSize: Typography.sizes.xl,
    fontWeight: Typography.weights.semibold,
    lineHeight: Typography.sizes.xl * Typography.lineHeights.normal,
  },
  lg: {
    fontSize: Typography.sizes.lg,
    fontWeight: Typography.weights.regular,
    lineHeight: Typography.sizes.lg * Typography.lineHeights.normal,
  },
  xl: {
    fontSize: Typography.sizes.xl,
    fontWeight: Typography.weights.regular,
    lineHeight: Typography.sizes.xl * Typography.lineHeights.normal,
  },
  xxl: {
    fontSize: Typography.sizes.xxl,
    fontWeight: Typography.weights.regular,
    lineHeight: Typography.sizes.xxl * Typography.lineHeights.normal,
  },
  body: {
    fontSize: Typography.sizes.md,
    fontWeight: Typography.weights.regular,
    lineHeight: Typography.sizes.md * Typography.lineHeights.normal,
  },
  bodySmall: {
    fontSize: Typography.sizes.sm,
    fontWeight: Typography.weights.regular,
    lineHeight: Typography.sizes.sm * Typography.lineHeights.normal,
  },
  caption: {
    fontSize: Typography.sizes.xs,
    fontWeight: Typography.weights.regular,
    lineHeight: Typography.sizes.xs * Typography.lineHeights.normal,
  },
  label: {
    fontSize: Typography.sizes.sm,
    fontWeight: Typography.weights.medium,
    lineHeight: Typography.sizes.sm * Typography.lineHeights.normal,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
};

const colorMap: Record<TextColor, string> = {
  primary: Colors.text,
  secondary: Colors.textSecondary,
  muted: Colors.textMuted,
  success: Colors.success,
  warning: Colors.warning,
  error: Colors.error,
  inverse: Colors.textInverse,
};

export function Text({
  children,
  variant = 'body',
  color = 'primary',
  weight,
  align,
  style,
  numberOfLines,
}: TextProps) {
  return (
    <RNText
      numberOfLines={numberOfLines}
      style={[
        variantStyles[variant],
        { color: colorMap[color] },
        weight && { fontWeight: Typography.weights[weight] },
        align && { textAlign: align },
        style,
      ]}
    >
      {children}
    </RNText>
  );
}
