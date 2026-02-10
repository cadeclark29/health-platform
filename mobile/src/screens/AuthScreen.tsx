// AuthScreen - Sign in screen

import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Text, Button, Card } from '../components';
import { Colors, Spacing, BorderRadius, Typography } from '../constants/theme';
import { useAppState } from '../hooks/useAppState';

export function AuthScreen() {
  const { signIn, isLoading } = useAppState();
  const [email, setEmail] = useState('');

  const handleSignIn = async () => {
    if (!email.trim()) {
      Alert.alert('Error', 'Please enter your email');
      return;
    }

    try {
      await signIn(email.trim().toLowerCase());
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to sign in');
    }
  };

  return (
    <LinearGradient
      colors={[Colors.background, '#0F0A1A', Colors.background]}
      style={styles.gradient}
    >
      <SafeAreaView style={styles.container}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.keyboardView}
        >
          {/* Logo/Brand */}
          <View style={styles.header}>
            <View style={styles.logoContainer}>
              <LinearGradient
                colors={[Colors.primary, Colors.primaryDark]}
                style={styles.logoGradient}
              >
                <Text variant="h1" style={styles.logoText}>H</Text>
              </LinearGradient>
            </View>
            <Text variant="h1" weight="bold" style={styles.title}>
              Health Platform
            </Text>
            <Text variant="body" color="secondary" align="center">
              AI-powered supplement recommendations{'\n'}based on your biometrics
            </Text>
          </View>

          {/* Sign In Card */}
          <Card style={styles.card} padding="lg">
            <Text variant="h3" weight="semibold" style={styles.cardTitle}>
              Welcome Back
            </Text>
            <Text variant="bodySmall" color="secondary" style={styles.cardSubtitle}>
              Sign in with your email to continue
            </Text>

            <View style={styles.inputContainer}>
              <Text variant="label" color="secondary" style={styles.inputLabel}>
                Email
              </Text>
              <TextInput
                style={styles.input}
                placeholder="you@example.com"
                placeholderTextColor={Colors.textMuted}
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                autoComplete="email"
                keyboardType="email-address"
                returnKeyType="go"
                onSubmitEditing={handleSignIn}
              />
            </View>

            <Button
              title={isLoading ? 'Signing in...' : 'Sign In'}
              onPress={handleSignIn}
              loading={isLoading}
              fullWidth
              size="lg"
            />

            <Text variant="caption" color="muted" align="center" style={styles.hint}>
              Don't have an account? Sign in with your email and we'll create one for you.
            </Text>
          </Card>

          {/* Features */}
          <View style={styles.features}>
            <FeatureItem
              icon="📊"
              title="Track Health Metrics"
              description="Sync with Oura Ring"
            />
            <FeatureItem
              icon="💊"
              title="Smart Supplements"
              description="Personalized doses"
            />
            <FeatureItem
              icon="📈"
              title="See Your Progress"
              description="Analytics & insights"
            />
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </LinearGradient>
  );
}

function FeatureItem({
  icon,
  title,
  description,
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <View style={styles.featureItem}>
      <Text style={styles.featureIcon}>{icon}</Text>
      <View>
        <Text variant="bodySmall" weight="medium">{title}</Text>
        <Text variant="caption" color="muted">{description}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  gradient: {
    flex: 1,
  },
  container: {
    flex: 1,
  },
  keyboardView: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: Spacing.xl,
  },

  header: {
    alignItems: 'center',
    marginBottom: Spacing.xxxl,
  },
  logoContainer: {
    marginBottom: Spacing.lg,
  },
  logoGradient: {
    width: 80,
    height: 80,
    borderRadius: BorderRadius.xl,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoText: {
    color: Colors.text,
    fontSize: 40,
  },
  title: {
    marginBottom: Spacing.sm,
  },

  card: {
    marginBottom: Spacing.xxxl,
  },
  cardTitle: {
    marginBottom: Spacing.xs,
  },
  cardSubtitle: {
    marginBottom: Spacing.xl,
  },

  inputContainer: {
    marginBottom: Spacing.lg,
  },
  inputLabel: {
    marginBottom: Spacing.xs,
  },
  input: {
    backgroundColor: Colors.background,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    fontSize: Typography.sizes.md,
    color: Colors.text,
  },

  hint: {
    marginTop: Spacing.lg,
  },

  features: {
    gap: Spacing.md,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  featureIcon: {
    fontSize: 24,
  },
});
