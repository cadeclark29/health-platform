// AddSupplementModal - Modal for adding new supplements

import React, { useState } from 'react';
import {
  Modal,
  View,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Pressable,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  FlatList,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { Text } from './Text';
import { Button } from './Button';
import { Colors, Spacing, BorderRadius } from '../constants/theme';
import { TimeSlot } from '../types';

interface AddSupplementModalProps {
  visible: boolean;
  onClose: () => void;
  onAdd: (data: {
    supplement_id: string;
    supplement_name: string;
    dosage: string;
    timeSlot: TimeSlot;
  }) => void;
  existingSupplements: string[];
}

const COMMON_SUPPLEMENTS = [
  // Vitamins
  { id: 'vitamin_d3', name: 'Vitamin D3', defaultDose: '2000 IU', defaultTime: 'morning' as TimeSlot },
  { id: 'vitamin_b12', name: 'Vitamin B12', defaultDose: '1000 mcg', defaultTime: 'morning' as TimeSlot },
  { id: 'vitamin_b_complex', name: 'Vitamin B Complex', defaultDose: '1 capsule', defaultTime: 'morning' as TimeSlot },
  { id: 'vitamin_c', name: 'Vitamin C', defaultDose: '500 mg', defaultTime: 'morning' as TimeSlot },
  { id: 'vitamin_k2', name: 'Vitamin K2', defaultDose: '100 mcg', defaultTime: 'morning' as TimeSlot },

  // Minerals
  { id: 'magnesium_glycinate', name: 'Magnesium Glycinate', defaultDose: '400 mg', defaultTime: 'evening' as TimeSlot },
  { id: 'magnesium_l_threonate', name: 'Magnesium L-Threonate', defaultDose: '144 mg', defaultTime: 'evening' as TimeSlot },
  { id: 'zinc', name: 'Zinc', defaultDose: '15 mg', defaultTime: 'evening' as TimeSlot },
  { id: 'iron', name: 'Iron', defaultDose: '18 mg', defaultTime: 'morning' as TimeSlot },
  { id: 'electrolytes', name: 'Electrolytes', defaultDose: '1 serving', defaultTime: 'intraday' as TimeSlot },

  // Omega-3s
  { id: 'fish_oil', name: 'Fish Oil / Omega-3', defaultDose: '2 g', defaultTime: 'morning' as TimeSlot },
  { id: 'cod_liver_oil', name: 'Cod Liver Oil', defaultDose: '1 tsp', defaultTime: 'morning' as TimeSlot },

  // Nootropics & Adaptogens
  { id: 'lions_mane', name: "Lion's Mane", defaultDose: '500 mg', defaultTime: 'morning' as TimeSlot },
  { id: 'ashwagandha', name: 'Ashwagandha', defaultDose: '300 mg', defaultTime: 'evening' as TimeSlot },
  { id: 'rhodiola', name: 'Rhodiola Rosea', defaultDose: '200 mg', defaultTime: 'morning' as TimeSlot },
  { id: 'cordyceps', name: 'Cordyceps', defaultDose: '500 mg', defaultTime: 'morning' as TimeSlot },
  { id: 'l_theanine', name: 'L-Theanine', defaultDose: '200 mg', defaultTime: 'evening' as TimeSlot },

  // Sleep
  { id: 'melatonin', name: 'Melatonin', defaultDose: '0.5 mg', defaultTime: 'evening' as TimeSlot },
  { id: 'glycine', name: 'Glycine', defaultDose: '3 g', defaultTime: 'evening' as TimeSlot },
  { id: 'apigenin', name: 'Apigenin', defaultDose: '50 mg', defaultTime: 'evening' as TimeSlot },
  { id: 'gaba', name: 'GABA', defaultDose: '250 mg', defaultTime: 'evening' as TimeSlot },
  { id: 'valerian', name: 'Valerian Root', defaultDose: '300 mg', defaultTime: 'evening' as TimeSlot },

  // Performance
  { id: 'creatine', name: 'Creatine Monohydrate', defaultDose: '5 g', defaultTime: 'intraday' as TimeSlot },
  { id: 'coq10', name: 'CoQ10', defaultDose: '100 mg', defaultTime: 'morning' as TimeSlot },
  { id: 'alpha_lipoic_acid', name: 'Alpha Lipoic Acid', defaultDose: '300 mg', defaultTime: 'intraday' as TimeSlot },
  { id: 'caffeine', name: 'Caffeine', defaultDose: '100 mg', defaultTime: 'morning' as TimeSlot },

  // Other
  { id: 'probiotics', name: 'Probiotics', defaultDose: '1 capsule', defaultTime: 'morning' as TimeSlot },
  { id: 'collagen', name: 'Collagen', defaultDose: '10 g', defaultTime: 'morning' as TimeSlot },
  { id: 'turmeric', name: 'Turmeric / Curcumin', defaultDose: '500 mg', defaultTime: 'morning' as TimeSlot },
  { id: 'berberine', name: 'Berberine', defaultDose: '500 mg', defaultTime: 'morning' as TimeSlot },
];

const TIME_SLOTS: { value: TimeSlot; label: string; icon: string }[] = [
  { value: 'morning', label: 'Morning', icon: '🌅' },
  { value: 'intraday', label: 'Intra-Day', icon: '☀️' },
  { value: 'evening', label: 'Evening', icon: '🌙' },
];

const COMMON_UNITS = ['mg', 'g', 'mcg', 'IU', 'ml', 'capsules', 'tablets'];

export function AddSupplementModal({
  visible,
  onClose,
  onAdd,
  existingSupplements,
}: AddSupplementModalProps) {
  const [step, setStep] = useState<'select' | 'customize'>('select');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSupplement, setSelectedSupplement] = useState<typeof COMMON_SUPPLEMENTS[0] | null>(null);
  const [customName, setCustomName] = useState('');
  const [dosage, setDosage] = useState('');
  const [selectedTimeSlot, setSelectedTimeSlot] = useState<TimeSlot>('morning');

  const resetAndClose = () => {
    setStep('select');
    setSearchQuery('');
    setSelectedSupplement(null);
    setCustomName('');
    setDosage('');
    setSelectedTimeSlot('morning');
    onClose();
  };

  const filteredSupplements = COMMON_SUPPLEMENTS.filter(supp => {
    // Filter out already added supplements
    if (existingSupplements.includes(supp.id)) return false;
    // Filter by search query
    if (!searchQuery) return true;
    return supp.name.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const handleSelectSupplement = (supp: typeof COMMON_SUPPLEMENTS[0]) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setSelectedSupplement(supp);
    setDosage(supp.defaultDose);
    setSelectedTimeSlot(supp.defaultTime);
    setStep('customize');
  };

  const handleCustomSupplement = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    setSelectedSupplement(null);
    setCustomName(searchQuery);
    setDosage('');
    setSelectedTimeSlot('morning');
    setStep('customize');
  };

  const handleAdd = () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    const name = selectedSupplement?.name || customName;
    const id = selectedSupplement?.id || customName.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');

    onAdd({
      supplement_id: id,
      supplement_name: name,
      dosage,
      timeSlot: selectedTimeSlot,
    });
    resetAndClose();
  };

  const handleUnitPress = (unit: string) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    const num = dosage.replace(/[^0-9.]/g, '');
    setDosage(num ? `${num} ${unit}` : unit);
  };

  const handleTimeSlotChange = (slot: TimeSlot) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setSelectedTimeSlot(slot);
  };

  const renderSelectStep = () => (
    <>
      {/* Search Input */}
      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          value={searchQuery}
          onChangeText={setSearchQuery}
          placeholder="Search supplements..."
          placeholderTextColor={Colors.textMuted}
          autoCapitalize="none"
          autoCorrect={false}
        />
      </View>

      {/* Supplement List */}
      <FlatList
        data={filteredSupplements}
        keyExtractor={item => item.id}
        style={styles.list}
        showsVerticalScrollIndicator={false}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.supplementItem}
            onPress={() => handleSelectSupplement(item)}
          >
            <View style={styles.supplementInfo}>
              <Text variant="body" weight="medium">{item.name}</Text>
              <Text variant="caption" color="muted">
                {item.defaultDose} • {TIME_SLOTS.find(t => t.value === item.defaultTime)?.label}
              </Text>
            </View>
            <Text style={styles.addIcon}>+</Text>
          </TouchableOpacity>
        )}
        ListHeaderComponent={
          searchQuery.length > 0 && !filteredSupplements.some(s =>
            s.name.toLowerCase() === searchQuery.toLowerCase()
          ) ? (
            <TouchableOpacity
              style={[styles.supplementItem, styles.customItem]}
              onPress={handleCustomSupplement}
            >
              <View style={styles.supplementInfo}>
                <Text variant="body" weight="medium">Add "{searchQuery}"</Text>
                <Text variant="caption" color="muted">Create custom supplement</Text>
              </View>
              <Text style={[styles.addIcon, { color: Colors.primary }]}>+</Text>
            </TouchableOpacity>
          ) : null
        }
        ListEmptyComponent={
          <View style={styles.emptyList}>
            <Text variant="body" color="muted" align="center">
              No supplements found
            </Text>
            {searchQuery.length > 0 && (
              <Button
                title={`Add "${searchQuery}" as custom`}
                onPress={handleCustomSupplement}
                variant="ghost"
                style={styles.addCustomButton}
              />
            )}
          </View>
        }
      />
    </>
  );

  const renderCustomizeStep = () => (
    <ScrollView showsVerticalScrollIndicator={false}>
      {/* Back Button */}
      <TouchableOpacity
        style={styles.backButton}
        onPress={() => setStep('select')}
      >
        <Text variant="body" color="primary">← Back</Text>
      </TouchableOpacity>

      {/* Supplement Name */}
      <Text variant="h2" weight="bold" style={styles.supplementName}>
        {selectedSupplement?.name || customName}
      </Text>

      {/* Custom Name Input (only for custom supplements) */}
      {!selectedSupplement && (
        <View style={styles.section}>
          <Text variant="label" color="secondary" style={styles.sectionLabel}>
            Name
          </Text>
          <TextInput
            style={styles.input}
            value={customName}
            onChangeText={setCustomName}
            placeholder="Supplement name"
            placeholderTextColor={Colors.textMuted}
          />
        </View>
      )}

      {/* Dosage Input */}
      <View style={styles.section}>
        <Text variant="label" color="secondary" style={styles.sectionLabel}>
          Dosage
        </Text>
        <TextInput
          style={styles.input}
          value={dosage}
          onChangeText={setDosage}
          placeholder="e.g., 400 mg"
          placeholderTextColor={Colors.textMuted}
          keyboardType="default"
          autoCapitalize="none"
        />
        <View style={styles.unitsRow}>
          {COMMON_UNITS.map(unit => (
            <TouchableOpacity
              key={unit}
              style={[
                styles.unitButton,
                dosage.toLowerCase().includes(unit.toLowerCase()) && styles.unitButtonActive,
              ]}
              onPress={() => handleUnitPress(unit)}
            >
              <Text
                variant="caption"
                color={dosage.toLowerCase().includes(unit.toLowerCase()) ? 'primary' : 'secondary'}
                weight={dosage.toLowerCase().includes(unit.toLowerCase()) ? 'semibold' : 'regular'}
              >
                {unit}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Time Slot Selection */}
      <View style={styles.section}>
        <Text variant="label" color="secondary" style={styles.sectionLabel}>
          Time of Day
        </Text>
        <View style={styles.timeSlotsRow}>
          {TIME_SLOTS.map(slot => (
            <TouchableOpacity
              key={slot.value}
              style={[
                styles.timeSlotButton,
                selectedTimeSlot === slot.value && styles.timeSlotButtonActive,
              ]}
              onPress={() => handleTimeSlotChange(slot.value)}
            >
              <Text style={styles.timeSlotIcon}>{slot.icon}</Text>
              <Text
                variant="bodySmall"
                weight={selectedTimeSlot === slot.value ? 'semibold' : 'regular'}
                color={selectedTimeSlot === slot.value ? 'primary' : 'secondary'}
              >
                {slot.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Add Button */}
      <Button
        title="Add to Stack"
        onPress={handleAdd}
        variant="primary"
        fullWidth
        disabled={!dosage || (!selectedSupplement && !customName)}
        style={styles.addButton}
      />
    </ScrollView>
  );

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={resetAndClose}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.overlay}
      >
        <Pressable style={styles.backdrop} onPress={resetAndClose} />
        <View style={styles.content}>
          <View style={styles.handle} />

          {/* Header */}
          <View style={styles.header}>
            <Text variant="h3" weight="bold">
              {step === 'select' ? 'Add Supplement' : 'Customize'}
            </Text>
            <TouchableOpacity onPress={resetAndClose} style={styles.closeButton}>
              <Text style={styles.closeIcon}>✕</Text>
            </TouchableOpacity>
          </View>

          {step === 'select' ? renderSelectStep() : renderCustomizeStep()}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  content: {
    backgroundColor: Colors.backgroundElevated,
    borderTopLeftRadius: BorderRadius.xl,
    borderTopRightRadius: BorderRadius.xl,
    paddingHorizontal: Spacing.lg,
    paddingBottom: Spacing.xxxl,
    height: '85%',
  },
  handle: {
    width: 36,
    height: 4,
    backgroundColor: Colors.border,
    borderRadius: 2,
    alignSelf: 'center',
    marginTop: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.lg,
  },
  closeButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeIcon: {
    fontSize: 16,
    color: Colors.textMuted,
  },

  // Select Step
  searchContainer: {
    marginBottom: Spacing.md,
  },
  searchInput: {
    backgroundColor: Colors.background,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    fontSize: 16,
    color: Colors.text,
  },
  list: {
    flex: 1,
  },
  supplementItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  customItem: {
    backgroundColor: Colors.primaryLight,
    marginHorizontal: -Spacing.lg,
    paddingHorizontal: Spacing.lg,
    borderBottomWidth: 0,
    marginBottom: Spacing.sm,
  },
  supplementInfo: {
    flex: 1,
  },
  addIcon: {
    fontSize: 24,
    color: Colors.textMuted,
    marginLeft: Spacing.md,
  },
  emptyList: {
    paddingVertical: Spacing.xxl,
    alignItems: 'center',
  },
  addCustomButton: {
    marginTop: Spacing.md,
  },

  // Customize Step
  backButton: {
    marginBottom: Spacing.md,
  },
  supplementName: {
    marginBottom: Spacing.xl,
  },
  section: {
    marginBottom: Spacing.xl,
  },
  sectionLabel: {
    marginBottom: Spacing.sm,
  },
  input: {
    backgroundColor: Colors.background,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    fontSize: 16,
    color: Colors.text,
  },
  unitsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.xs,
    marginTop: Spacing.sm,
  },
  unitButton: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  unitButtonActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },
  timeSlotsRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  timeSlotButton: {
    flex: 1,
    flexDirection: 'column',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: Spacing.xs,
  },
  timeSlotButtonActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },
  timeSlotIcon: {
    fontSize: 24,
  },
  addButton: {
    marginTop: Spacing.md,
  },
});
