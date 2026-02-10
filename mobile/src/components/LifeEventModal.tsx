// LifeEventModal - Add and manage life events

import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  Modal,
  Pressable,
  ScrollView,
  TextInput,
  Alert,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { Text, Button, Card } from './index';
import { Colors, Spacing, BorderRadius, Typography } from '../constants/theme';
import { LifeEvent, LIFE_EVENT_TYPES } from '../types';

interface LifeEventModalProps {
  visible: boolean;
  onClose: () => void;
  onAdd: (data: { event_type: string; event_date: string; description?: string }) => Promise<void>;
  onDelete: (eventId: string) => Promise<void>;
  events: LifeEvent[];
  getDateString: (date: Date) => string;
}

export function LifeEventModal({
  visible,
  onClose,
  onAdd,
  onDelete,
  events,
  getDateString,
}: LifeEventModalProps) {
  const [mode, setMode] = useState<'list' | 'add'>('list');
  const [selectedType, setSelectedType] = useState('');
  const [description, setDescription] = useState('');
  const [eventDate, setEventDate] = useState(getDateString(new Date()));
  const [saving, setSaving] = useState(false);

  const isValidDate = (dateStr: string): boolean => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return false;
    const d = new Date(dateStr + 'T00:00:00');
    return !isNaN(d.getTime());
  };

  const handleAdd = async () => {
    if (!selectedType) {
      Alert.alert('Select Type', 'Please select an event type');
      return;
    }

    if (!isValidDate(eventDate)) {
      Alert.alert('Invalid Date', 'Please enter a valid date in YYYY-MM-DD format');
      return;
    }

    setSaving(true);
    try {
      await onAdd({
        event_type: selectedType,
        event_date: eventDate,
        description: description.trim() || undefined,
      });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      resetForm();
      setMode('list');
    } catch (error) {
      Alert.alert('Error', 'Failed to add life event');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = (event: LifeEvent) => {
    Alert.alert(
      'Delete Event',
      `Remove "${getEventLabel(event.event_type)}" event?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await onDelete(event.id);
              Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
            } catch (error) {
              Alert.alert('Error', 'Failed to delete event');
            }
          },
        },
      ]
    );
  };

  const resetForm = () => {
    setSelectedType('');
    setDescription('');
    setEventDate(getDateString(new Date()));
  };

  const getEventLabel = (type: string) => {
    return LIFE_EVENT_TYPES.find(t => t.value === type)?.label || type;
  };

  const getEventIcon = (type: string) => {
    return LIFE_EVENT_TYPES.find(t => t.value === type)?.icon || '📝';
  };

  const formatDisplayDate = (dateStr: string) => {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const sortedEvents = [...events].sort((a, b) => b.event_date.localeCompare(a.event_date));

  return (
    <Modal visible={visible} transparent animationType="slide">
      <Pressable style={styles.overlay} onPress={onClose}>
        <Pressable style={styles.modal}>
          {/* Header */}
          <View style={styles.header}>
            <View>
              <Text variant="h3" weight="semibold">Life Events</Text>
              <Text variant="caption" color="muted">Track changes that affect your health</Text>
            </View>
            <Pressable onPress={onClose} style={styles.closeBtn}>
              <Text variant="h3" color="muted">x</Text>
            </Pressable>
          </View>

          {mode === 'list' ? (
            <>
              {/* Add button */}
              <Pressable
                style={styles.addNewBtn}
                onPress={() => {
                  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                  setMode('add');
                }}
              >
                <Text variant="body" color="primary" weight="semibold">+ Add Life Event</Text>
              </Pressable>

              {/* Event list */}
              <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
                {sortedEvents.length === 0 ? (
                  <View style={styles.emptyState}>
                    <Text variant="body" color="muted" align="center">
                      No life events logged yet
                    </Text>
                    <Text variant="caption" color="muted" align="center" style={styles.emptyHint}>
                      Life events help correlate health changes with real-world context
                    </Text>
                  </View>
                ) : (
                  sortedEvents.map(event => (
                    <View key={event.id} style={styles.eventCard}>
                      <View style={styles.eventLeft}>
                        <Text style={styles.eventIcon}>{getEventIcon(event.event_type)}</Text>
                        <View style={styles.eventInfo}>
                          <Text variant="body" weight="medium">{getEventLabel(event.event_type)}</Text>
                          <Text variant="caption" color="muted">{formatDisplayDate(event.event_date)}</Text>
                          {event.description && (
                            <Text variant="caption" color="secondary" style={styles.eventDesc}>
                              {event.description}
                            </Text>
                          )}
                        </View>
                      </View>
                      <Pressable onPress={() => handleDelete(event)} style={styles.deleteBtn}>
                        <Text variant="caption" color="error">Delete</Text>
                      </Pressable>
                    </View>
                  ))
                )}
              </ScrollView>
            </>
          ) : (
            <>
              {/* Add form */}
              <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
                <Pressable onPress={() => setMode('list')} style={styles.backLink}>
                  <Text variant="bodySmall" color="primary">← Back to list</Text>
                </Pressable>

                {/* Date */}
                <View style={styles.formGroup}>
                  <Text variant="label" color="secondary" style={styles.label}>Date</Text>
                  <TextInput
                    style={styles.input}
                    value={eventDate}
                    onChangeText={setEventDate}
                    placeholder="YYYY-MM-DD"
                    placeholderTextColor={Colors.textMuted}
                  />
                </View>

                {/* Event type grid */}
                <View style={styles.formGroup}>
                  <Text variant="label" color="secondary" style={styles.label}>Event Type</Text>
                  <View style={styles.typeGrid}>
                    {LIFE_EVENT_TYPES.map(type => {
                      const isSelected = selectedType === type.value;
                      return (
                        <Pressable
                          key={type.value}
                          style={[styles.typeCard, isSelected && styles.typeCardActive]}
                          onPress={() => {
                            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                            setSelectedType(type.value);
                          }}
                        >
                          <Text style={styles.typeIcon}>{type.icon}</Text>
                          <Text
                            variant="caption"
                            weight={isSelected ? 'semibold' : 'regular'}
                            color={isSelected ? 'primary' : 'secondary'}
                            align="center"
                            numberOfLines={2}
                          >
                            {type.label}
                          </Text>
                        </Pressable>
                      );
                    })}
                  </View>
                </View>

                {/* Description */}
                <View style={styles.formGroup}>
                  <Text variant="label" color="secondary" style={styles.label}>
                    Description (optional)
                  </Text>
                  <TextInput
                    style={[styles.input, styles.textArea]}
                    value={description}
                    onChangeText={setDescription}
                    placeholder="e.g., Started running 3x/week"
                    placeholderTextColor={Colors.textMuted}
                    multiline
                    numberOfLines={3}
                  />
                </View>

                <Button
                  title={saving ? 'Adding...' : 'Add Event'}
                  onPress={handleAdd}
                  variant="primary"
                  fullWidth
                  loading={saving}
                />
              </ScrollView>
            </>
          )}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: Colors.overlay,
    justifyContent: 'flex-end',
  },
  modal: {
    backgroundColor: Colors.backgroundCard,
    borderTopLeftRadius: BorderRadius.xl,
    borderTopRightRadius: BorderRadius.xl,
    maxHeight: '85%',
    paddingBottom: Spacing.xxxl,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: Spacing.xl,
    paddingTop: Spacing.xl,
    paddingBottom: Spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  closeBtn: {
    padding: Spacing.sm,
  },
  scrollView: {
    paddingHorizontal: Spacing.xl,
    maxHeight: 500,
  },

  // Add button
  addNewBtn: {
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },

  // Event cards
  eventCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: Spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  eventLeft: {
    flexDirection: 'row',
    flex: 1,
    gap: Spacing.md,
  },
  eventIcon: {
    fontSize: 20,
    marginTop: 2,
  },
  eventInfo: {
    flex: 1,
    gap: 2,
  },
  eventDesc: {
    marginTop: Spacing.xs,
  },
  deleteBtn: {
    padding: Spacing.sm,
  },

  // Empty state
  emptyState: {
    paddingVertical: Spacing.xxxl,
    alignItems: 'center',
  },
  emptyHint: {
    marginTop: Spacing.sm,
    paddingHorizontal: Spacing.xl,
  },

  // Form
  backLink: {
    paddingVertical: Spacing.md,
  },
  formGroup: {
    marginBottom: Spacing.xl,
  },
  label: {
    marginBottom: Spacing.sm,
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
  textArea: {
    minHeight: 80,
    textAlignVertical: 'top',
  },

  // Type grid
  typeGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  typeCard: {
    width: '31%',
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.xs,
    borderRadius: BorderRadius.md,
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: 'center',
    gap: Spacing.xs,
  },
  typeCardActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },
  typeIcon: {
    fontSize: 20,
  },
});
