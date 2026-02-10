// OnboardingScreen - 7-step onboarding wizard for new users

import React, { useState, useRef } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TextInput,
  Pressable,
  Animated,
  Linking,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Haptics from 'expo-haptics';
import { Text, Button, Card } from '../components';
import { Colors, Spacing, BorderRadius, Typography } from '../constants/theme';
import { useAppState } from '../hooks/useAppState';
import { api } from '../services/api';
import { User, TimeSlot } from '../types';

const TOTAL_STEPS = 7;
const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Pre-built supplement stacks for quick selection
const QUICK_STACKS = [
  {
    name: 'Sleep Stack',
    icon: '😴',
    supplements: [
      { id: 'magnesium_glycinate', name: 'Magnesium Glycinate', dose: '400 mg', time: 'evening' as TimeSlot },
      { id: 'l_theanine', name: 'L-Theanine', dose: '200 mg', time: 'evening' as TimeSlot },
      { id: 'glycine', name: 'Glycine', dose: '3 g', time: 'evening' as TimeSlot },
    ],
  },
  {
    name: 'Energy Stack',
    icon: '⚡',
    supplements: [
      { id: 'vitamin_b_complex', name: 'Vitamin B Complex', dose: '1 capsule', time: 'morning' as TimeSlot },
      { id: 'coq10', name: 'CoQ10', dose: '200 mg', time: 'morning' as TimeSlot },
      { id: 'rhodiola', name: 'Rhodiola', dose: '300 mg', time: 'morning' as TimeSlot },
    ],
  },
  {
    name: 'Recovery Stack',
    icon: '💪',
    supplements: [
      { id: 'omega_3', name: 'Omega-3 Fish Oil', dose: '2 g', time: 'morning' as TimeSlot },
      { id: 'creatine', name: 'Creatine', dose: '5 g', time: 'intraday' as TimeSlot },
      { id: 'ashwagandha', name: 'Ashwagandha', dose: '300 mg', time: 'evening' as TimeSlot },
    ],
  },
  {
    name: 'Wellness Stack',
    icon: '🌿',
    supplements: [
      { id: 'vitamin_d3', name: 'Vitamin D3', dose: '2000 IU', time: 'morning' as TimeSlot },
      { id: 'omega_3', name: 'Omega-3 Fish Oil', dose: '2 g', time: 'morning' as TimeSlot },
      { id: 'magnesium_glycinate', name: 'Magnesium Glycinate', dose: '400 mg', time: 'evening' as TimeSlot },
    ],
  },
];

// Common supplements for manual selection
const COMMON_SUPPLEMENTS = [
  { id: 'vitamin_d3', name: 'Vitamin D3', dose: '2000 IU', time: 'morning' as TimeSlot },
  { id: 'omega_3', name: 'Omega-3 Fish Oil', dose: '2 g', time: 'morning' as TimeSlot },
  { id: 'magnesium_glycinate', name: 'Magnesium Glycinate', dose: '400 mg', time: 'evening' as TimeSlot },
  { id: 'ashwagandha', name: 'Ashwagandha', dose: '300 mg', time: 'evening' as TimeSlot },
  { id: 'creatine', name: 'Creatine', dose: '5 g', time: 'intraday' as TimeSlot },
  { id: 'vitamin_b12', name: 'Vitamin B12', dose: '1000 mcg', time: 'morning' as TimeSlot },
  { id: 'zinc', name: 'Zinc', dose: '15 mg', time: 'evening' as TimeSlot },
  { id: 'iron', name: 'Iron', dose: '18 mg', time: 'morning' as TimeSlot },
  { id: 'l_theanine', name: 'L-Theanine', dose: '200 mg', time: 'evening' as TimeSlot },
  { id: 'glycine', name: 'Glycine', dose: '3 g', time: 'evening' as TimeSlot },
  { id: 'melatonin', name: 'Melatonin', dose: '0.5 mg', time: 'evening' as TimeSlot },
  { id: 'coq10', name: 'CoQ10', dose: '200 mg', time: 'morning' as TimeSlot },
  { id: 'rhodiola', name: 'Rhodiola', dose: '300 mg', time: 'morning' as TimeSlot },
  { id: 'lions_mane', name: "Lion's Mane", dose: '500 mg', time: 'morning' as TimeSlot },
  { id: 'cordyceps', name: 'Cordyceps', dose: '500 mg', time: 'morning' as TimeSlot },
  { id: 'apigenin', name: 'Apigenin', dose: '50 mg', time: 'evening' as TimeSlot },
  { id: 'alpha_lipoic_acid', name: 'Alpha Lipoic Acid', dose: '300 mg', time: 'intraday' as TimeSlot },
  { id: 'electrolytes', name: 'Electrolytes', dose: '1 serving', time: 'intraday' as TimeSlot },
  { id: 'vitamin_b_complex', name: 'Vitamin B Complex', dose: '1 capsule', time: 'morning' as TimeSlot },
  { id: 'fish_oil', name: 'Fish Oil', dose: '2 g', time: 'morning' as TimeSlot },
  { id: 'magnesium_l_threonate', name: 'Magnesium L-Threonate', dose: '2 g', time: 'evening' as TimeSlot },
  { id: 'gaba', name: 'GABA', dose: '250 mg', time: 'evening' as TimeSlot },
  { id: 'valerian', name: 'Valerian Root', dose: '300 mg', time: 'evening' as TimeSlot },
];

export function OnboardingScreen() {
  const { user, userId, updateUser, addSupplement, completeOnboarding, updateSupplementTiming } = useAppState();
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const progressAnim = useRef(new Animated.Value(1 / TOTAL_STEPS)).current;

  // Step 1 - About You
  const [age, setAge] = useState(user?.age?.toString() || '');
  const [sex, setSex] = useState<string>(user?.sex || '');
  const [heightFeet, setHeightFeet] = useState(user?.height_feet?.toString() || '');
  const [heightInches, setHeightInches] = useState(user?.height_inches?.toString() || '');
  const [weight, setWeight] = useState(user?.weight_lbs?.toString() || '');

  // Step 2 - Lifestyle
  const [region, setRegion] = useState<string>(user?.region || '');
  const [activityLevel, setActivityLevel] = useState<string>(user?.activity_level || '');
  const [workEnvironment, setWorkEnvironment] = useState<string>(user?.work_environment || '');
  const [dietType, setDietType] = useState<string>(user?.diet_type || '');

  // Step 3 - Chronotype
  const [chronotype, setChronotype] = useState<string>(user?.chronotype || '');

  // Step 5 - Supplements
  const [selectedSupplements, setSelectedSupplements] = useState<typeof COMMON_SUPPLEMENTS>([]);
  const [supplementSearch, setSupplementSearch] = useState('');

  // Step 6 - Goals
  const [goals, setGoals] = useState<string[]>([]);

  const animateProgress = (toStep: number) => {
    Animated.spring(progressAnim, {
      toValue: toStep / TOTAL_STEPS,
      useNativeDriver: false,
      tension: 50,
      friction: 10,
    }).start();
  };

  const goNext = async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

    // Save data per step
    try {
      setSaving(true);
      if (step === 1 && userId) {
        const updates: Partial<User> = {};
        const parseNum = (val: string) => { const n = parseInt(val, 10); return isNaN(n) ? undefined : n; };
        if (age) updates.age = parseNum(age);
        if (sex) updates.sex = sex as any;
        if (heightFeet) updates.height_feet = parseNum(heightFeet);
        if (heightInches) updates.height_inches = parseNum(heightInches);
        if (weight) updates.weight_lbs = parseNum(weight);
        if (Object.keys(updates).length > 0) {
          await updateUser(updates);
        }
      } else if (step === 2 && userId) {
        const updates: Partial<User> = {};
        if (region) updates.region = region as any;
        if (activityLevel) updates.activity_level = activityLevel as any;
        if (workEnvironment) updates.work_environment = workEnvironment as any;
        if (dietType) updates.diet_type = dietType as any;
        if (Object.keys(updates).length > 0) {
          await updateUser(updates);
        }
      } else if (step === 3 && userId && chronotype) {
        await updateUser({ chronotype: chronotype as any });
      } else if (step === 5 && selectedSupplements.length > 0) {
        // Add each supplement
        for (const supp of selectedSupplements) {
          try {
            await addSupplement({
              supplement_id: supp.id,
              supplement_name: supp.name,
              dosage: supp.dose,
              timeSlot: supp.time,
            });
          } catch {
            // Skip if already exists
          }
        }
      } else if (step === 6 && goals.length > 0 && userId) {
        await updateUser({ health_goal: goals[0] as any });
      }
    } catch (error) {
      console.error('Error saving onboarding step:', error);
    } finally {
      setSaving(false);
    }

    if (step < TOTAL_STEPS) {
      const next = step + 1;
      setStep(next);
      animateProgress(next);
    }
  };

  const goBack = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    if (step > 1) {
      const prev = step - 1;
      setStep(prev);
      animateProgress(prev);
    }
  };

  const handleComplete = async () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    try {
      setSaving(true);
      await completeOnboarding();
    } catch (error) {
      console.error('Error completing onboarding:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleConnectOura = () => {
    if (userId) {
      const authUrl = api.getOuraAuthUrl(userId);
      Linking.openURL(authUrl);
    }
  };

  const toggleSupplement = (supp: typeof COMMON_SUPPLEMENTS[0]) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setSelectedSupplements(prev => {
      const exists = prev.find(s => s.id === supp.id);
      if (exists) {
        return prev.filter(s => s.id !== supp.id);
      }
      return [...prev, supp];
    });
  };

  const addQuickStack = (stack: typeof QUICK_STACKS[0]) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setSelectedSupplements(prev => {
      const newSupps = [...prev];
      for (const supp of stack.supplements) {
        if (!newSupps.find(s => s.id === supp.id)) {
          newSupps.push(supp);
        }
      }
      return newSupps;
    });
  };

  const toggleGoal = (goal: string) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setGoals(prev => {
      if (prev.includes(goal)) {
        return prev.filter(g => g !== goal);
      }
      if (prev.length >= 4) return prev;
      return [...prev, goal];
    });
  };

  const filteredSupplements = supplementSearch
    ? COMMON_SUPPLEMENTS.filter(s =>
        s.name.toLowerCase().includes(supplementSearch.toLowerCase())
      )
    : COMMON_SUPPLEMENTS;

  const progressWidth = progressAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
  });

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      {/* Progress Bar */}
      <View style={styles.progressContainer}>
        <View style={styles.progressBar}>
          <Animated.View style={[styles.progressFill, { width: progressWidth }]} />
        </View>
        <Text variant="caption" color="muted" style={styles.stepText}>
          Step {step} of {TOTAL_STEPS}
        </Text>
      </View>

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.flex}
      >
        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {/* Step 1: About You */}
          {step === 1 && (
            <View style={styles.stepContainer}>
              <Text variant="h2" weight="bold" style={styles.stepTitle}>About You</Text>
              <Text variant="body" color="secondary" style={styles.stepSubtitle}>
                Help us personalize your supplement recommendations
              </Text>

              <View style={styles.formGroup}>
                <Text variant="label" color="secondary" style={styles.label}>Age</Text>
                <TextInput
                  style={styles.input}
                  placeholder="e.g., 28"
                  placeholderTextColor={Colors.textMuted}
                  value={age}
                  onChangeText={setAge}
                  keyboardType="number-pad"
                  maxLength={3}
                />
              </View>

              <View style={styles.formGroup}>
                <Text variant="label" color="secondary" style={styles.label}>Biological Sex</Text>
                <View style={styles.optionRow}>
                  {[
                    { value: 'male', label: 'Male' },
                    { value: 'female', label: 'Female' },
                    { value: 'other', label: 'Other' },
                  ].map(opt => (
                    <Pressable
                      key={opt.value}
                      style={[styles.optionChip, sex === opt.value && styles.optionChipActive]}
                      onPress={() => setSex(opt.value)}
                    >
                      <Text
                        variant="bodySmall"
                        weight={sex === opt.value ? 'semibold' : 'regular'}
                        color={sex === opt.value ? 'primary' : 'secondary'}
                      >
                        {opt.label}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </View>

              <View style={styles.formGroup}>
                <Text variant="label" color="secondary" style={styles.label}>Height</Text>
                <View style={styles.heightRow}>
                  <View style={styles.heightInput}>
                    <TextInput
                      style={styles.input}
                      placeholder="ft"
                      placeholderTextColor={Colors.textMuted}
                      value={heightFeet}
                      onChangeText={setHeightFeet}
                      keyboardType="number-pad"
                      maxLength={1}
                    />
                    <Text variant="caption" color="muted">ft</Text>
                  </View>
                  <View style={styles.heightInput}>
                    <TextInput
                      style={styles.input}
                      placeholder="in"
                      placeholderTextColor={Colors.textMuted}
                      value={heightInches}
                      onChangeText={setHeightInches}
                      keyboardType="number-pad"
                      maxLength={2}
                    />
                    <Text variant="caption" color="muted">in</Text>
                  </View>
                </View>
              </View>

              <View style={styles.formGroup}>
                <Text variant="label" color="secondary" style={styles.label}>Weight (lbs)</Text>
                <TextInput
                  style={styles.input}
                  placeholder="e.g., 175"
                  placeholderTextColor={Colors.textMuted}
                  value={weight}
                  onChangeText={setWeight}
                  keyboardType="number-pad"
                  maxLength={3}
                />
              </View>
            </View>
          )}

          {/* Step 2: Lifestyle */}
          {step === 2 && (
            <View style={styles.stepContainer}>
              <Text variant="h2" weight="bold" style={styles.stepTitle}>Your Lifestyle</Text>
              <Text variant="body" color="secondary" style={styles.stepSubtitle}>
                These help optimize recommendations for your environment
              </Text>

              <View style={styles.formGroup}>
                <Text variant="label" color="secondary" style={styles.label}>Region</Text>
                <View style={styles.cardGrid}>
                  {[
                    { value: 'northern', label: 'Northern US', desc: 'Less sunlight', icon: '🏔️' },
                    { value: 'central', label: 'Central US', desc: 'Moderate climate', icon: '🌾' },
                    { value: 'southern', label: 'Southern US', desc: 'More sunlight', icon: '☀️' },
                    { value: 'gulf', label: 'Gulf Coast', desc: 'Humid & warm', icon: '🌊' },
                  ].map(opt => (
                    <Pressable
                      key={opt.value}
                      style={[styles.selectCard, region === opt.value && styles.selectCardActive]}
                      onPress={() => setRegion(opt.value)}
                    >
                      <Text style={styles.selectCardIcon}>{opt.icon}</Text>
                      <Text variant="bodySmall" weight="medium" color={region === opt.value ? 'primary' : 'secondary'}>
                        {opt.label}
                      </Text>
                      <Text variant="caption" color="muted">{opt.desc}</Text>
                    </Pressable>
                  ))}
                </View>
              </View>

              <View style={styles.formGroup}>
                <Text variant="label" color="secondary" style={styles.label}>Activity Level</Text>
                <View style={styles.optionColumn}>
                  {[
                    { value: 'sedentary', label: 'Sedentary', desc: 'Little to no exercise' },
                    { value: 'light', label: 'Lightly Active', desc: '1-2 days/week' },
                    { value: 'moderate', label: 'Moderately Active', desc: '3-5 days/week' },
                    { value: 'active', label: 'Active', desc: '6-7 days/week' },
                    { value: 'athlete', label: 'Athlete', desc: 'Intense training' },
                  ].map(opt => (
                    <Pressable
                      key={opt.value}
                      style={[styles.listOption, activityLevel === opt.value && styles.listOptionActive]}
                      onPress={() => setActivityLevel(opt.value)}
                    >
                      <View>
                        <Text variant="body" weight={activityLevel === opt.value ? 'semibold' : 'regular'}
                              color={activityLevel === opt.value ? 'primary' : 'secondary'}>
                          {opt.label}
                        </Text>
                        <Text variant="caption" color="muted">{opt.desc}</Text>
                      </View>
                      {activityLevel === opt.value && (
                        <Text variant="body" color="primary">✓</Text>
                      )}
                    </Pressable>
                  ))}
                </View>
              </View>

              <View style={styles.formGroup}>
                <Text variant="label" color="secondary" style={styles.label}>Diet Type</Text>
                <View style={styles.optionRow}>
                  {[
                    { value: 'omnivore', label: 'Omnivore' },
                    { value: 'vegetarian', label: 'Vegetarian' },
                    { value: 'vegan', label: 'Vegan' },
                  ].map(opt => (
                    <Pressable
                      key={opt.value}
                      style={[styles.optionChip, dietType === opt.value && styles.optionChipActive]}
                      onPress={() => setDietType(opt.value)}
                    >
                      <Text
                        variant="bodySmall"
                        weight={dietType === opt.value ? 'semibold' : 'regular'}
                        color={dietType === opt.value ? 'primary' : 'secondary'}
                      >
                        {opt.label}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            </View>
          )}

          {/* Step 3: Sleep Style */}
          {step === 3 && (
            <View style={styles.stepContainer}>
              <Text variant="h2" weight="bold" style={styles.stepTitle}>Sleep Style</Text>
              <Text variant="body" color="secondary" style={styles.stepSubtitle}>
                Your chronotype affects supplement timing recommendations
              </Text>

              <View style={styles.chronoCards}>
                {[
                  { value: 'early_bird', label: 'Early Bird', icon: '🌅', desc: 'I wake up easily before 7am and feel most productive in the morning' },
                  { value: 'night_owl', label: 'Night Owl', icon: '🌙', desc: 'I come alive at night and struggle with early mornings' },
                  { value: 'neutral', label: 'Flexible', icon: '⚖️', desc: "I can adapt to either schedule without much trouble" },
                ].map(opt => (
                  <Pressable
                    key={opt.value}
                    style={[styles.chronoCard, chronotype === opt.value && styles.chronoCardActive]}
                    onPress={() => setChronotype(opt.value)}
                  >
                    <Text style={styles.chronoIcon}>{opt.icon}</Text>
                    <Text variant="lg" weight="semibold" color={chronotype === opt.value ? 'primary' : 'secondary'}>
                      {opt.label}
                    </Text>
                    <Text variant="bodySmall" color="muted" align="center" style={styles.chronoDesc}>
                      {opt.desc}
                    </Text>
                    {chronotype === opt.value && (
                      <View style={styles.chronoCheck}>
                        <Text variant="body" color="primary">✓</Text>
                      </View>
                    )}
                  </Pressable>
                ))}
              </View>
            </View>
          )}

          {/* Step 4: Connect Oura */}
          {step === 4 && (
            <View style={styles.stepContainer}>
              <Text variant="h2" weight="bold" style={styles.stepTitle}>Connect Oura Ring</Text>
              <Text variant="body" color="secondary" style={styles.stepSubtitle}>
                Get personalized recommendations based on your biometrics
              </Text>

              <Card style={styles.ouraCard}>
                <View style={styles.ouraBenefits}>
                  {[
                    { icon: '💤', text: 'Personalized sleep recommendations based on sleep scores' },
                    { icon: '❤️', text: 'Recovery-based dosing adjusted to your HRV' },
                    { icon: '📊', text: 'Track supplement impact on your health metrics' },
                    { icon: '🎯', text: 'Smart alerts when metrics need attention' },
                  ].map((item, i) => (
                    <View key={i} style={styles.benefitRow}>
                      <Text style={styles.benefitIcon}>{item.icon}</Text>
                      <Text variant="bodySmall" color="secondary" style={styles.benefitText}>{item.text}</Text>
                    </View>
                  ))}
                </View>

                <Button
                  title="Connect Oura Ring"
                  onPress={handleConnectOura}
                  variant="primary"
                  fullWidth
                  size="lg"
                />

                <Text variant="caption" color="muted" align="center" style={styles.ouraSkipText}>
                  You can connect later from Settings
                </Text>
              </Card>
            </View>
          )}

          {/* Step 5: Your Supplements */}
          {step === 5 && (
            <View style={styles.stepContainer}>
              <Text variant="h2" weight="bold" style={styles.stepTitle}>What Do You Take?</Text>
              <Text variant="body" color="secondary" style={styles.stepSubtitle}>
                Select supplements you're currently taking
              </Text>

              {/* Quick stacks */}
              <Text variant="label" color="secondary" style={styles.label}>Quick Add Stacks</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.stackScroll}>
                {QUICK_STACKS.map(stack => (
                  <Pressable
                    key={stack.name}
                    style={styles.quickStack}
                    onPress={() => addQuickStack(stack)}
                  >
                    <Text style={styles.quickStackIcon}>{stack.icon}</Text>
                    <Text variant="bodySmall" weight="medium">{stack.name}</Text>
                    <Text variant="caption" color="muted">{stack.supplements.length} supps</Text>
                  </Pressable>
                ))}
              </ScrollView>

              {/* Search */}
              <View style={styles.searchContainer}>
                <TextInput
                  style={styles.searchInput}
                  placeholder="Search supplements..."
                  placeholderTextColor={Colors.textMuted}
                  value={supplementSearch}
                  onChangeText={setSupplementSearch}
                />
              </View>

              {/* Selected count */}
              {selectedSupplements.length > 0 && (
                <View style={styles.selectedCount}>
                  <Text variant="bodySmall" color="primary" weight="semibold">
                    {selectedSupplements.length} selected
                  </Text>
                  <Pressable onPress={() => setSelectedSupplements([])}>
                    <Text variant="caption" color="muted">Clear all</Text>
                  </Pressable>
                </View>
              )}

              {/* Supplement list */}
              <View style={styles.suppList}>
                {filteredSupplements.map(supp => {
                  const isSelected = selectedSupplements.some(s => s.id === supp.id);
                  return (
                    <Pressable
                      key={supp.id}
                      style={[styles.suppItem, isSelected && styles.suppItemActive]}
                      onPress={() => toggleSupplement(supp)}
                    >
                      <View style={styles.suppItemInfo}>
                        <Text variant="body" weight={isSelected ? 'semibold' : 'regular'}
                              color={isSelected ? 'primary' : 'secondary'}>
                          {supp.name}
                        </Text>
                        <Text variant="caption" color="muted">{supp.dose}</Text>
                      </View>
                      <View style={[styles.suppCheck, isSelected && styles.suppCheckActive]}>
                        {isSelected && <Text variant="caption" style={{ color: '#fff' }}>✓</Text>}
                      </View>
                    </Pressable>
                  );
                })}
              </View>
            </View>
          )}

          {/* Step 6: Health Goals */}
          {step === 6 && (
            <View style={styles.stepContainer}>
              <Text variant="h2" weight="bold" style={styles.stepTitle}>What's Your Focus?</Text>
              <Text variant="body" color="secondary" style={styles.stepSubtitle}>
                Select up to 4 goals to prioritize your recommendations
              </Text>

              <View style={styles.goalGrid}>
                {[
                  { value: 'sleep', label: 'Better Sleep', icon: '😴', desc: 'Improve sleep quality, duration, and deep sleep' },
                  { value: 'recovery', label: 'Recovery & Performance', icon: '💪', desc: 'Faster recovery, better HRV, reduced inflammation' },
                  { value: 'energy', label: 'Energy & Focus', icon: '⚡', desc: 'More sustained energy and mental clarity' },
                  { value: 'wellness', label: 'General Wellness', icon: '🌿', desc: 'Overall health optimization and longevity' },
                ].map(goal => {
                  const isSelected = goals.includes(goal.value);
                  return (
                    <Pressable
                      key={goal.value}
                      style={[styles.goalCard, isSelected && styles.goalCardActive]}
                      onPress={() => toggleGoal(goal.value)}
                    >
                      <Text style={styles.goalIcon}>{goal.icon}</Text>
                      <Text variant="body" weight="semibold" color={isSelected ? 'primary' : 'secondary'}>
                        {goal.label}
                      </Text>
                      <Text variant="caption" color="muted" align="center">
                        {goal.desc}
                      </Text>
                      {isSelected && (
                        <View style={styles.goalCheck}>
                          <Text variant="caption" style={{ color: Colors.primary }}>✓</Text>
                        </View>
                      )}
                    </Pressable>
                  );
                })}
              </View>

              {goals.length > 0 && (
                <Text variant="caption" color="muted" align="center" style={styles.goalCount}>
                  {goals.length}/4 goals selected
                </Text>
              )}
            </View>
          )}

          {/* Step 7: Complete */}
          {step === 7 && (
            <View style={styles.stepContainer}>
              <View style={styles.completeHeader}>
                <View style={styles.completeBadge}>
                  <Text style={styles.completeEmoji}>🎉</Text>
                </View>
                <Text variant="h2" weight="bold" align="center" style={styles.stepTitle}>
                  You're All Set!
                </Text>
                <Text variant="body" color="secondary" align="center" style={styles.stepSubtitle}>
                  Your personalized health platform is ready
                </Text>
              </View>

              <Card style={styles.summaryCard}>
                <Text variant="label" color="secondary" style={styles.summaryLabel}>Your Setup</Text>
                <View style={styles.summaryList}>
                  <SummaryItem
                    label="Profile"
                    value={age ? `${age} yrs, ${sex || 'not set'}` : 'Skipped'}
                    done={!!age}
                  />
                  <SummaryItem
                    label="Lifestyle"
                    value={activityLevel ? formatActivity(activityLevel) : 'Skipped'}
                    done={!!activityLevel}
                  />
                  <SummaryItem
                    label="Sleep Style"
                    value={chronotype ? formatChrono(chronotype) : 'Skipped'}
                    done={!!chronotype}
                  />
                  <SummaryItem
                    label="Oura Ring"
                    value="Connect anytime"
                    done={false}
                  />
                  <SummaryItem
                    label="Supplements"
                    value={selectedSupplements.length > 0 ? `${selectedSupplements.length} added` : 'None yet'}
                    done={selectedSupplements.length > 0}
                  />
                  <SummaryItem
                    label="Goals"
                    value={goals.length > 0 ? goals.map(g => formatGoalShort(g)).join(', ') : 'Skipped'}
                    done={goals.length > 0}
                  />
                </View>
              </Card>

              <Button
                title="Start Using CustomDose"
                onPress={handleComplete}
                variant="primary"
                fullWidth
                size="lg"
                loading={saving}
              />
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>

      {/* Bottom Navigation */}
      {step < 7 && (
        <View style={styles.bottomNav}>
          {step > 1 ? (
            <Pressable onPress={goBack} style={styles.backBtn}>
              <Text variant="body" color="secondary">Back</Text>
            </Pressable>
          ) : (
            <View style={styles.backBtn} />
          )}

          <Button
            title={saving ? 'Saving...' : step === 6 ? 'Finish' : 'Continue'}
            onPress={goNext}
            variant="primary"
            loading={saving}
            size="md"
          />

          <Pressable onPress={goNext} style={styles.skipBtn}>
            <Text variant="bodySmall" color="muted">Skip</Text>
          </Pressable>
        </View>
      )}
    </SafeAreaView>
  );
}

function SummaryItem({ label, value, done }: { label: string; value: string; done: boolean }) {
  return (
    <View style={styles.summaryItem}>
      <View style={[styles.summaryDot, done && styles.summaryDotDone]}>
        <Text variant="caption" style={{ color: done ? '#fff' : Colors.textMuted }}>
          {done ? '✓' : '○'}
        </Text>
      </View>
      <View style={styles.summaryItemText}>
        <Text variant="bodySmall" weight="medium">{label}</Text>
        <Text variant="caption" color="muted">{value}</Text>
      </View>
    </View>
  );
}

function formatActivity(val: string): string {
  const map: Record<string, string> = {
    sedentary: 'Sedentary', light: 'Light', moderate: 'Moderate',
    active: 'Active', athlete: 'Athlete',
  };
  return map[val] || val;
}

function formatChrono(val: string): string {
  const map: Record<string, string> = {
    early_bird: 'Early Bird', night_owl: 'Night Owl', neutral: 'Flexible',
  };
  return map[val] || val;
}

function formatGoalShort(val: string): string {
  const map: Record<string, string> = {
    sleep: 'Sleep', recovery: 'Recovery', energy: 'Energy', wellness: 'Wellness',
  };
  return map[val] || val;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  flex: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 120,
  },

  // Progress
  progressContainer: {
    paddingHorizontal: Spacing.xl,
    paddingTop: Spacing.md,
    paddingBottom: Spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  progressBar: {
    flex: 1,
    height: 4,
    backgroundColor: Colors.backgroundElevated,
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: Colors.primary,
    borderRadius: 2,
  },
  stepText: {
    minWidth: 70,
    textAlign: 'right',
  },

  // Step container
  stepContainer: {
    paddingHorizontal: Spacing.xl,
    paddingTop: Spacing.xl,
  },
  stepTitle: {
    marginBottom: Spacing.xs,
  },
  stepSubtitle: {
    marginBottom: Spacing.xxl,
  },

  // Form elements
  formGroup: {
    marginBottom: Spacing.xl,
  },
  label: {
    marginBottom: Spacing.sm,
    marginLeft: 2,
  },
  input: {
    backgroundColor: Colors.backgroundCard,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    fontSize: Typography.sizes.md,
    color: Colors.text,
  },
  heightRow: {
    flexDirection: 'row',
    gap: Spacing.md,
  },
  heightInput: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },

  // Option chips (row)
  optionRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  optionChip: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.backgroundCard,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  optionChipActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },

  // Option column (list)
  optionColumn: {
    gap: Spacing.sm,
  },
  listOption: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.backgroundCard,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  listOptionActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },

  // Card grid (2-column)
  cardGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  selectCard: {
    width: (SCREEN_WIDTH - Spacing.xl * 2 - Spacing.sm) / 2,
    paddingVertical: Spacing.lg,
    paddingHorizontal: Spacing.md,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.backgroundCard,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: 'center',
    gap: Spacing.xs,
  },
  selectCardActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },
  selectCardIcon: {
    fontSize: 24,
    marginBottom: Spacing.xs,
  },

  // Chronotype cards
  chronoCards: {
    gap: Spacing.md,
  },
  chronoCard: {
    paddingVertical: Spacing.xxl,
    paddingHorizontal: Spacing.xl,
    borderRadius: BorderRadius.lg,
    backgroundColor: Colors.backgroundCard,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: 'center',
    position: 'relative',
  },
  chronoCardActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },
  chronoIcon: {
    fontSize: 36,
    marginBottom: Spacing.md,
  },
  chronoDesc: {
    marginTop: Spacing.sm,
  },
  chronoCheck: {
    position: 'absolute',
    top: Spacing.md,
    right: Spacing.md,
  },

  // Oura card
  ouraCard: {
    marginTop: Spacing.md,
  },
  ouraBenefits: {
    marginBottom: Spacing.xl,
    gap: Spacing.lg,
  },
  benefitRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.md,
  },
  benefitIcon: {
    fontSize: 20,
  },
  benefitText: {
    flex: 1,
  },
  ouraSkipText: {
    marginTop: Spacing.md,
  },

  // Supplement selection
  stackScroll: {
    marginBottom: Spacing.lg,
  },
  quickStack: {
    width: 120,
    paddingVertical: Spacing.lg,
    paddingHorizontal: Spacing.md,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.backgroundCard,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: 'center',
    marginRight: Spacing.sm,
    gap: Spacing.xs,
  },
  quickStackIcon: {
    fontSize: 24,
  },
  searchContainer: {
    marginBottom: Spacing.md,
  },
  searchInput: {
    backgroundColor: Colors.backgroundCard,
    borderRadius: BorderRadius.full,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    fontSize: Typography.sizes.md,
    color: Colors.text,
  },
  selectedCount: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  suppList: {
    gap: Spacing.sm,
  },
  suppItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.backgroundCard,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  suppItemActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },
  suppItemInfo: {
    flex: 1,
  },
  suppCheck: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: Colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  suppCheckActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },

  // Goals
  goalGrid: {
    gap: Spacing.md,
  },
  goalCard: {
    paddingVertical: Spacing.xl,
    paddingHorizontal: Spacing.xl,
    borderRadius: BorderRadius.lg,
    backgroundColor: Colors.backgroundCard,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: 'center',
    position: 'relative',
    gap: Spacing.sm,
  },
  goalCardActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },
  goalIcon: {
    fontSize: 32,
  },
  goalCheck: {
    position: 'absolute',
    top: Spacing.md,
    right: Spacing.md,
  },
  goalCount: {
    marginTop: Spacing.lg,
  },

  // Complete step
  completeHeader: {
    alignItems: 'center',
    marginBottom: Spacing.xxl,
  },
  completeBadge: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.primaryLight,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.lg,
  },
  completeEmoji: {
    fontSize: 40,
  },
  summaryCard: {
    marginBottom: Spacing.xxl,
  },
  summaryLabel: {
    marginBottom: Spacing.md,
  },
  summaryList: {
    gap: Spacing.md,
  },
  summaryItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  summaryDot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: Colors.backgroundElevated,
    justifyContent: 'center',
    alignItems: 'center',
  },
  summaryDotDone: {
    backgroundColor: Colors.success,
  },
  summaryItemText: {
    flex: 1,
  },

  // Bottom nav
  bottomNav: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.lg,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.background,
  },
  backBtn: {
    minWidth: 50,
    paddingVertical: Spacing.sm,
  },
  skipBtn: {
    minWidth: 50,
    paddingVertical: Spacing.sm,
    alignItems: 'flex-end',
  },
});
