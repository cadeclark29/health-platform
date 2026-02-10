// AnalyticsScreen - Enhanced health trends, insights, life events, and supplement management

import React, { useState, useMemo } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
  Pressable,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Path, Circle, Line, Text as SvgText, G } from 'react-native-svg';
import * as Haptics from 'expo-haptics';
import { Text, Card, LifeEventModal } from '../components';
import { Colors, Spacing, BorderRadius } from '../constants/theme';
import { useAppState } from '../hooks/useAppState';
import { HealthData, SupplementInsight, SUPPLEMENT_MECHANISMS, LIFE_EVENT_TYPES } from '../types';

type TimeFrame = 7 | 14 | 30 | 60;
type MetricKey = 'sleep_score' | 'hrv_score' | 'recovery_score' | 'steps' | 'deep_sleep_pct' | 'resting_hr';

const METRIC_CONFIG: Record<MetricKey, { label: string; color: string; isDynamic: boolean }> = {
  sleep_score: { label: 'Sleep', color: Colors.sleep, isDynamic: false },
  hrv_score: { label: 'HRV', color: Colors.hrv, isDynamic: false },
  recovery_score: { label: 'Recovery', color: Colors.recovery, isDynamic: false },
  steps: { label: 'Steps', color: Colors.activity, isDynamic: true },
  deep_sleep_pct: { label: 'Deep %', color: '#A78BFA', isDynamic: false },
  resting_hr: { label: 'Rest HR', color: '#F87171', isDynamic: true },
};

const CHART_WIDTH = Dimensions.get('window').width - Spacing.lg * 2 - Spacing.lg * 2;
const CHART_HEIGHT = 160;

function formatSupplementName(id: string): string {
  return id
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getScoreColor(score: number | null | undefined): string {
  if (score == null) return Colors.textMuted;
  if (score >= 80) return Colors.success;
  if (score >= 60) return Colors.warning;
  return Colors.error;
}

export function AnalyticsScreen() {
  const {
    analyticsData,
    insightsData,
    refreshData,
    ouraConnected,
    removeSupplement,
    addLifeEvent,
    deleteLifeEvent,
    getDateString,
  } = useAppState();

  const [refreshing, setRefreshing] = useState(false);
  const [timeFrame, setTimeFrame] = useState<TimeFrame>(30);
  const [selectedMetric, setSelectedMetric] = useState<MetricKey>('sleep_score');
  const [selectedPoint, setSelectedPoint] = useState<{ date: string; data: HealthData } | null>(null);
  const [lifeEventModalVisible, setLifeEventModalVisible] = useState(false);

  const onRefresh = async () => {
    setRefreshing(true);
    await refreshData();
    setRefreshing(false);
  };

  const healthData = analyticsData?.health_data || [];
  const supplements = analyticsData?.supplement_starts?.filter(s => !s.end_date) || [];
  const supplementStarts = analyticsData?.supplement_starts || [];
  const lifeEvents = analyticsData?.life_events || [];
  const supplementLogs = analyticsData?.supplement_logs || [];

  // Filter health data by timeframe
  const filteredHealth = useMemo(() => {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - timeFrame);
    return healthData
      .filter(h => new Date(h.date) >= cutoffDate)
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [healthData, timeFrame]);

  // Calculate averages
  const calcAvg = (data: HealthData[], key: keyof HealthData): number | null => {
    const values = data
      .map(d => d[key])
      .filter((v): v is number => v != null && typeof v === 'number');
    if (values.length === 0) return null;
    return Math.round(values.reduce((a, b) => a + b, 0) / values.length);
  };

  const avgSleep = calcAvg(filteredHealth, 'sleep_score');
  const avgHrv = calcAvg(filteredHealth, 'hrv_score');
  const avgRecovery = calcAvg(filteredHealth, 'recovery_score');

  // Adherence calculation
  const adherenceData = useMemo(() => {
    return supplements.map(supp => {
      const suppId = supp.supplement_id?.toLowerCase().replace(/-/g, '_');
      const startDate = new Date(supp.start_date + 'T00:00:00');
      const today = new Date();
      const daysSinceStart = Math.max(1, Math.floor((today.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)));
      const logsForSupp = supplementLogs.filter(l => {
        const logId = l.supplement_id?.toLowerCase().replace(/-/g, '_');
        return logId === suppId;
      });
      const uniqueDays = new Set(logsForSupp.map(l => l.date)).size;
      const adherencePct = Math.min(100, Math.round((uniqueDays / daysSinceStart) * 100));
      return {
        id: supp.id,
        name: supp.supplement_name || formatSupplementName(suppId),
        suppId,
        daysSinceStart,
        daysLogged: uniqueDays,
        adherencePct,
      };
    });
  }, [supplements, supplementLogs]);

  const handleDeleteSupplement = (suppId: string, name: string) => {
    Alert.alert(
      'Remove Supplement',
      `Are you sure you want to remove ${name} from your stack?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await removeSupplement(suppId);
            } catch (error) {
              Alert.alert('Error', 'Failed to remove supplement');
            }
          },
        },
      ]
    );
  };

  // Build chart data with dynamic scaling
  const buildChartPath = (data: HealthData[], key: MetricKey) => {
    const config = METRIC_CONFIG[key];
    const values = data.map(d => {
      const val = d[key];
      return typeof val === 'number' ? val : null;
    });

    const validValues = values.filter((v): v is number => v != null);
    if (validValues.length < 2) return { path: '', points: [], min: 0, max: 100 };

    let min: number, max: number;
    if (config.isDynamic) {
      min = Math.min(...validValues);
      max = Math.max(...validValues);
      const range = max - min || 1;
      min = Math.max(0, min - range * 0.1);
      max = max + range * 0.1;
    } else {
      min = 0;
      max = 100;
    }

    const validPoints: { x: number; y: number; value: number; date: string }[] = [];
    values.forEach((v, i) => {
      if (v != null) {
        validPoints.push({
          x: (i / Math.max(data.length - 1, 1)) * CHART_WIDTH,
          y: CHART_HEIGHT - ((v - min) / (max - min)) * CHART_HEIGHT,
          value: v,
          date: data[i].date,
        });
      }
    });

    let path = `M ${validPoints[0].x} ${validPoints[0].y}`;
    for (let i = 1; i < validPoints.length; i++) {
      const prev = validPoints[i - 1];
      const curr = validPoints[i];
      const cpx = (prev.x + curr.x) / 2;
      path += ` C ${cpx} ${prev.y}, ${cpx} ${curr.y}, ${curr.x} ${curr.y}`;
    }

    return { path, points: validPoints, min, max };
  };

  // Chart markers for supplement starts and life events
  const chartMarkers = useMemo(() => {
    if (filteredHealth.length < 2) return { suppMarkers: [], eventMarkers: [] };

    const startDate = filteredHealth[0].date;
    const endDate = filteredHealth[filteredHealth.length - 1].date;
    const totalDays = filteredHealth.length - 1;

    const rawMarkers = supplementStarts
      .filter(s => s.start_date >= startDate && s.start_date <= endDate)
      .map(s => {
        const idx = filteredHealth.findIndex(h => h.date === s.start_date);
        if (idx < 0) return null;
        const x = (idx / Math.max(totalDays, 1)) * CHART_WIDTH;
        const name = s.supplement_name || formatSupplementName(s.supplement_id?.toLowerCase().replace(/-/g, '_'));
        return { x, name, date: s.start_date };
      })
      .filter(Boolean) as { x: number; name: string; date: string }[];

    // Group by date to prevent overlapping labels
    const markersByDate = new Map<string, { x: number; names: string[]; date: string }>();
    rawMarkers.forEach(m => {
      const existing = markersByDate.get(m.date);
      if (existing) {
        existing.names.push(m.name);
      } else {
        markersByDate.set(m.date, { x: m.x, names: [m.name], date: m.date });
      }
    });
    const suppMarkers = Array.from(markersByDate.values()).map(g => {
      let name: string;
      if (g.names.length === 1) {
        name = g.names[0];
      } else if (g.names.length === 2) {
        name = g.names[0].slice(0, 10) + ', ' + g.names[1].slice(0, 10);
      } else {
        name = g.names[0].slice(0, 10) + ' +' + (g.names.length - 1) + ' more';
      }
      return { x: g.x, name, date: g.date };
    });

    const eventMarkers = lifeEvents
      .filter(e => e.event_date >= startDate && e.event_date <= endDate)
      .map(e => {
        const idx = filteredHealth.findIndex(h => h.date === e.event_date);
        if (idx < 0) return null;
        const x = (idx / Math.max(totalDays, 1)) * CHART_WIDTH;
        return { x, type: e.event_type, date: e.event_date };
      })
      .filter(Boolean) as { x: number; type: string; date: string }[];

    return { suppMarkers, eventMarkers };
  }, [filteredHealth, supplementStarts, lifeEvents]);

  const chartData = buildChartPath(filteredHealth, selectedMetric);
  const metricColor = METRIC_CONFIG[selectedMetric].color;

  const handlePointTap = (date: string) => {
    const data = filteredHealth.find(h => h.date === date);
    if (data) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      setSelectedPoint(selectedPoint?.date === date ? null : { date, data });
    }
  };

  const getEventLabel = (type: string) => {
    return LIFE_EVENT_TYPES.find(t => t.value === type)?.label || type;
  };

  const getEventIcon = (type: string) => {
    return LIFE_EVENT_TYPES.find(t => t.value === type)?.icon || '📝';
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={Colors.primary}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text variant="h2" weight="bold">Analytics</Text>
        </View>

        {/* Timeframe Selector */}
        <View style={styles.timeframeContainer}>
          {([7, 14, 30, 60] as TimeFrame[]).map((days) => (
            <Pressable
              key={days}
              style={[
                styles.timeframeBtn,
                timeFrame === days && styles.timeframeBtnActive,
              ]}
              onPress={() => setTimeFrame(days)}
            >
              <Text
                variant="bodySmall"
                weight={timeFrame === days ? 'semibold' : 'regular'}
                color={timeFrame === days ? 'primary' : 'secondary'}
              >
                {days}d
              </Text>
            </Pressable>
          ))}
        </View>

        {/* Metric Selector Tabs */}
        {ouraConnected && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.metricSelectorContent}
            style={styles.metricSelector}
          >
            {(Object.keys(METRIC_CONFIG) as MetricKey[]).map((key) => (
              <Pressable
                key={key}
                style={[
                  styles.metricTab,
                  selectedMetric === key && {
                    backgroundColor: METRIC_CONFIG[key].color + '20',
                    borderColor: METRIC_CONFIG[key].color,
                  },
                ]}
                onPress={() => {
                  Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                  setSelectedMetric(key);
                  setSelectedPoint(null);
                }}
              >
                <Text
                  variant="caption"
                  weight={selectedMetric === key ? 'semibold' : 'regular'}
                  style={{ color: selectedMetric === key ? METRIC_CONFIG[key].color : Colors.textSecondary }}
                >
                  {METRIC_CONFIG[key].label}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        )}

        {/* Average Scores Card */}
        {ouraConnected && (
          <Card style={styles.averagesCard}>
            <Text variant="label" color="secondary" style={styles.sectionLabel}>
              {timeFrame}-Day Averages
            </Text>
            <View style={styles.averagesRow}>
              <View style={styles.averageItem}>
                <Text variant="h2" weight="bold" style={{ color: Colors.sleep }}>
                  {avgSleep ?? '--'}
                </Text>
                <Text variant="caption" color="secondary">Sleep</Text>
              </View>
              <View style={styles.averageItem}>
                <Text variant="h2" weight="bold" style={{ color: Colors.hrv }}>
                  {avgHrv ?? '--'}
                </Text>
                <Text variant="caption" color="secondary">HRV</Text>
              </View>
              <View style={styles.averageItem}>
                <Text variant="h2" weight="bold" style={{ color: Colors.recovery }}>
                  {avgRecovery ?? '--'}
                </Text>
                <Text variant="caption" color="secondary">Recovery</Text>
              </View>
            </View>
            <Text variant="caption" color="muted" align="center" style={styles.dataPoints}>
              Based on {filteredHealth.length} data points
            </Text>
          </Card>
        )}

        {/* Trend Chart */}
        {ouraConnected && filteredHealth.length >= 2 && (
          <Card style={styles.chartCard}>
            <Text variant="label" color="secondary" style={styles.sectionLabel}>
              {METRIC_CONFIG[selectedMetric].label} Trend
            </Text>
            <View style={styles.chartContainer}>
              <Svg
                width={CHART_WIDTH}
                height={CHART_HEIGHT + 30}
                viewBox={`0 -15 ${CHART_WIDTH} ${CHART_HEIGHT + 30}`}
              >
                {/* Grid lines */}
                {[0, 25, 50, 75, 100].map(pct => {
                  const y = CHART_HEIGHT - (pct / 100) * CHART_HEIGHT;
                  return (
                    <Line
                      key={pct}
                      x1={0} y1={y} x2={CHART_WIDTH} y2={y}
                      stroke={Colors.border}
                      strokeWidth={1}
                    />
                  );
                })}

                {/* Supplement start markers - vertical dashed lines */}
                {chartMarkers.suppMarkers.map((m, i) => (
                  <G key={`supp-${i}`}>
                    <Line
                      x1={m.x} y1={-10} x2={m.x} y2={CHART_HEIGHT}
                      stroke={Colors.primary}
                      strokeWidth={1}
                      strokeDasharray="4,4"
                      opacity={0.6}
                    />
                    <SvgText
                      x={m.x} y={-12}
                      fontSize={8}
                      fill={Colors.primary}
                      textAnchor="middle"
                      opacity={0.8}
                    >
                      {m.name.length > 10 ? m.name.slice(0, 10) + '...' : m.name}
                    </SvgText>
                  </G>
                ))}

                {/* Life event markers - dots at bottom */}
                {chartMarkers.eventMarkers.map((m, i) => (
                  <G key={`event-${i}`}>
                    <Line
                      x1={m.x} y1={CHART_HEIGHT - 5}
                      x2={m.x} y2={CHART_HEIGHT + 10}
                      stroke={Colors.warning}
                      strokeWidth={1.5}
                      opacity={0.6}
                    />
                    <Circle
                      cx={m.x} cy={CHART_HEIGHT + 10}
                      r={4}
                      fill={Colors.warning}
                      opacity={0.8}
                    />
                  </G>
                ))}

                {/* Trend line */}
                {chartData.path && (
                  <Path
                    d={chartData.path}
                    stroke={metricColor}
                    strokeWidth={2.5}
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                )}

                {/* Tappable data points */}
                {chartData.points.map((pt, i) => (
                  <G key={i}>
                    <Circle
                      cx={pt.x} cy={pt.y} r={12}
                      fill="transparent"
                      onPress={() => handlePointTap(pt.date)}
                    />
                    <Circle
                      cx={pt.x} cy={pt.y}
                      r={selectedPoint?.date === pt.date ? 5 : 3}
                      fill={selectedPoint?.date === pt.date ? '#fff' : metricColor}
                      stroke={selectedPoint?.date === pt.date ? metricColor : 'none'}
                      strokeWidth={2}
                    />
                  </G>
                ))}
              </Svg>
            </View>

            {/* Date labels */}
            <View style={styles.chartDateLabels}>
              <Text variant="caption" color="muted">
                {filteredHealth.length > 0 ? formatDate(filteredHealth[0].date) : ''}
              </Text>
              <Text variant="caption" color="muted">
                {filteredHealth.length > 0 ? formatDate(filteredHealth[filteredHealth.length - 1].date) : ''}
              </Text>
            </View>

            {/* Selected point detail */}
            {selectedPoint && (
              <View style={styles.pointDetail}>
                <Text variant="caption" weight="semibold" color="primary">
                  {formatDate(selectedPoint.date)}
                </Text>
                <View style={styles.pointDetailRow}>
                  <View style={styles.pointDetailItem}>
                    <Text variant="caption" color="muted">Sleep</Text>
                    <Text variant="bodySmall" weight="medium" style={{ color: getScoreColor(selectedPoint.data.sleep_score) }}>
                      {selectedPoint.data.sleep_score != null ? Math.round(selectedPoint.data.sleep_score) : '--'}
                    </Text>
                  </View>
                  <View style={styles.pointDetailItem}>
                    <Text variant="caption" color="muted">HRV</Text>
                    <Text variant="bodySmall" weight="medium" style={{ color: getScoreColor(selectedPoint.data.hrv_score) }}>
                      {selectedPoint.data.hrv_score != null ? Math.round(selectedPoint.data.hrv_score) : '--'}
                    </Text>
                  </View>
                  <View style={styles.pointDetailItem}>
                    <Text variant="caption" color="muted">Recovery</Text>
                    <Text variant="bodySmall" weight="medium" style={{ color: getScoreColor(selectedPoint.data.recovery_score) }}>
                      {selectedPoint.data.recovery_score != null ? Math.round(selectedPoint.data.recovery_score) : '--'}
                    </Text>
                  </View>
                  <View style={styles.pointDetailItem}>
                    <Text variant="caption" color="muted">Steps</Text>
                    <Text variant="bodySmall" weight="medium">
                      {selectedPoint.data.steps != null ? selectedPoint.data.steps.toLocaleString() : '--'}
                    </Text>
                  </View>
                  <View style={styles.pointDetailItem}>
                    <Text variant="caption" color="muted">HR</Text>
                    <Text variant="bodySmall" weight="medium">
                      {selectedPoint.data.resting_hr != null ? Math.round(selectedPoint.data.resting_hr) : '--'}
                    </Text>
                  </View>
                </View>
              </View>
            )}
          </Card>
        )}

        {/* Supplement Insights */}
        {insightsData && insightsData.impact_analysis?.length > 0 && (
          <View style={styles.insightsSection}>
            <View style={styles.sectionHeader}>
              <Text variant="h3" weight="semibold">Supplement Insights</Text>
              <Text variant="caption" color="muted">
                {insightsData.summary?.with_data || 0} of {insightsData.summary?.total_supplements || 0} with data
              </Text>
            </View>

            {insightsData.impact_analysis.map((insight) => (
              <InsightCard key={insight.supplement_id} insight={insight} />
            ))}
          </View>
        )}

        {/* Life Events Section */}
        <View style={styles.lifeEventsSection}>
          <View style={styles.sectionHeader}>
            <Text variant="h3" weight="semibold">Life Events</Text>
            <Pressable
              style={styles.addEventBtn}
              onPress={() => {
                Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                setLifeEventModalVisible(true);
              }}
            >
              <Text variant="caption" color="primary" weight="semibold">+ Manage</Text>
            </Pressable>
          </View>

          {lifeEvents.length === 0 ? (
            <Card style={styles.emptyCard}>
              <Text variant="bodySmall" color="muted" align="center">
                Track life changes that affect your health
              </Text>
              <Pressable
                style={styles.addEventLink}
                onPress={() => setLifeEventModalVisible(true)}
              >
                <Text variant="bodySmall" color="primary" weight="medium">Add your first event</Text>
              </Pressable>
            </Card>
          ) : (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.eventsScroll}
            >
              {lifeEvents
                .sort((a, b) => b.event_date.localeCompare(a.event_date))
                .slice(0, 5)
                .map(event => (
                  <View key={event.id} style={styles.eventChip}>
                    <Text style={styles.eventChipIcon}>{getEventIcon(event.event_type)}</Text>
                    <View>
                      <Text variant="caption" weight="medium" numberOfLines={1}>
                        {getEventLabel(event.event_type)}
                      </Text>
                      <Text variant="caption" color="muted">{formatDate(event.event_date)}</Text>
                    </View>
                  </View>
                ))}
            </ScrollView>
          )}
        </View>

        {/* Adherence Section */}
        {adherenceData.length > 0 && (
          <View style={styles.adherenceSection}>
            <Text variant="h3" weight="semibold" style={styles.sectionTitle}>
              Adherence
            </Text>
            {adherenceData.map(item => (
              <View key={item.id} style={styles.adherenceRow}>
                <View style={styles.adherenceInfo}>
                  <Text variant="bodySmall" weight="medium" numberOfLines={1}>{item.name}</Text>
                  <Text variant="caption" color="muted">
                    {item.daysLogged} of {item.daysSinceStart} days
                  </Text>
                </View>
                <View style={styles.adherenceBarContainer}>
                  <View style={styles.adherenceBarBg}>
                    <View
                      style={[
                        styles.adherenceBarFill,
                        {
                          width: `${item.adherencePct}%`,
                          backgroundColor: item.adherencePct >= 80 ? Colors.success
                            : item.adherencePct >= 50 ? Colors.warning
                            : Colors.error,
                        },
                      ]}
                    />
                  </View>
                  <Text variant="caption" weight="semibold" style={{
                    color: item.adherencePct >= 80 ? Colors.success
                      : item.adherencePct >= 50 ? Colors.warning
                      : Colors.error,
                    width: 36,
                    textAlign: 'right',
                  }}>
                    {item.adherencePct}%
                  </Text>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Supplements Section */}
        <View style={styles.supplementsSection}>
          <View style={styles.supplementsHeader}>
            <Text variant="h3" weight="semibold">Your Supplements</Text>
            <Text variant="caption" color="muted">
              {supplements.length} active
            </Text>
          </View>

          {supplements.length === 0 ? (
            <Card style={styles.emptyCard}>
              <Text variant="body" color="secondary" align="center">
                No supplements added yet
              </Text>
              <Text variant="caption" color="muted" align="center" style={styles.emptyHint}>
                Add supplements from the Dashboard to track them here
              </Text>
            </Card>
          ) : (
            supplements.map((supp) => {
              const suppId = supp.supplement_id?.toLowerCase().replace(/-/g, '_');
              const name = supp.supplement_name || formatSupplementName(suppId);
              const daysSince = Math.floor(
                (new Date().getTime() - new Date(supp.start_date + 'T00:00:00').getTime()) / (1000 * 60 * 60 * 24)
              );

              return (
                <Card key={supp.id} style={styles.supplementCard}>
                  <View style={styles.supplementRow}>
                    <View style={styles.supplementInfo}>
                      <Text variant="body" weight="semibold">{name}</Text>
                      <View style={styles.supplementMeta}>
                        {supp.dosage && (
                          <View style={styles.doseBadge}>
                            <Text variant="caption" color="primary" weight="medium">{supp.dosage}</Text>
                          </View>
                        )}
                        {supp.frequency && (
                          <Text variant="caption" color="muted">{supp.frequency}</Text>
                        )}
                      </View>
                      <Text variant="caption" color="muted">
                        Since {formatDate(supp.start_date)} ({daysSince}d)
                      </Text>
                    </View>
                    <Pressable
                      onPress={() => handleDeleteSupplement(supp.id, name)}
                      style={styles.removeBtn}
                    >
                      <Text variant="caption" color="error">Remove</Text>
                    </Pressable>
                  </View>
                </Card>
              );
            })
          )}
        </View>

        {/* Recent Data Table (expanded) */}
        {ouraConnected && filteredHealth.length > 0 && (
          <View style={styles.recentSection}>
            <Text variant="h3" weight="semibold" style={styles.sectionTitle}>
              Recent Data
            </Text>

            <View style={styles.tableHeader}>
              <Text variant="caption" color="muted" style={styles.tableDate}>Date</Text>
              <Text variant="caption" color="muted" style={styles.tableScore}>Sleep</Text>
              <Text variant="caption" color="muted" style={styles.tableScore}>HRV</Text>
              <Text variant="caption" color="muted" style={styles.tableScore}>Rec</Text>
              <Text variant="caption" color="muted" style={styles.tableScore}>Steps</Text>
              <Text variant="caption" color="muted" style={styles.tableScore}>Deep</Text>
              <Text variant="caption" color="muted" style={styles.tableScore}>HR</Text>
            </View>

            {filteredHealth.slice(-10).reverse().map((h) => (
              <View key={h.date} style={styles.tableRow}>
                <Text variant="caption" color="secondary" style={styles.tableDate}>
                  {formatDate(h.date)}
                </Text>
                <View style={styles.tableScore}>
                  <Text
                    variant="caption"
                    weight="medium"
                    style={{ color: getScoreColor(h.sleep_score) }}
                  >
                    {h.sleep_score != null ? Math.round(h.sleep_score) : '--'}
                  </Text>
                </View>
                <View style={styles.tableScore}>
                  <Text
                    variant="caption"
                    weight="medium"
                    style={{ color: getScoreColor(h.hrv_score) }}
                  >
                    {h.hrv_score != null ? Math.round(h.hrv_score) : '--'}
                  </Text>
                </View>
                <View style={styles.tableScore}>
                  <Text
                    variant="caption"
                    weight="medium"
                    style={{ color: getScoreColor(h.recovery_score) }}
                  >
                    {h.recovery_score != null ? Math.round(h.recovery_score) : '--'}
                  </Text>
                </View>
                <View style={styles.tableScore}>
                  <Text variant="caption" color="secondary">
                    {h.steps != null ? (h.steps > 999 ? `${(h.steps / 1000).toFixed(1)}k` : h.steps) : '--'}
                  </Text>
                </View>
                <View style={styles.tableScore}>
                  <Text variant="caption" color="secondary">
                    {h.deep_sleep_pct != null ? `${Math.round(h.deep_sleep_pct)}%` : '--'}
                  </Text>
                </View>
                <View style={styles.tableScore}>
                  <Text variant="caption" color="secondary">
                    {h.resting_hr != null ? Math.round(h.resting_hr) : '--'}
                  </Text>
                </View>
              </View>
            ))}
          </View>
        )}
      </ScrollView>

      {/* Life Events Modal */}
      <LifeEventModal
        visible={lifeEventModalVisible}
        onClose={() => setLifeEventModalVisible(false)}
        onAdd={addLifeEvent}
        onDelete={deleteLifeEvent}
        events={lifeEvents}
        getDateString={getDateString}
      />
    </SafeAreaView>
  );
}

// InsightCard - Shows before/after impact for a supplement
function InsightCard({ insight }: { insight: SupplementInsight }) {
  const mechanism = SUPPLEMENT_MECHANISMS[insight.supplement_id] || null;
  const changePct = insight.change_pct;
  const isPositive = insight.is_positive;
  const hasData = insight.has_sufficient_data;

  return (
    <Card style={styles.insightCard}>
      <View style={styles.insightHeader}>
        <View style={styles.insightNameRow}>
          <Text variant="body" weight="semibold">{insight.supplement_name}</Text>
          <Text variant="caption" color="muted">{insight.days_on}d</Text>
        </View>
        {hasData && changePct != null && (
          <View style={[
            styles.changeBadge,
            { backgroundColor: isPositive ? Colors.successLight : Colors.errorLight },
          ]}>
            <Text
              variant="caption"
              weight="semibold"
              style={{ color: isPositive ? Colors.success : Colors.error }}
            >
              {isPositive ? '+' : ''}{changePct.toFixed(1)}%
            </Text>
          </View>
        )}
      </View>

      {hasData ? (
        <>
          <Text variant="caption" color="secondary" style={styles.insightMetric}>
            {insight.metric_display_name}
          </Text>
          <View style={styles.insightBars}>
            <View style={styles.insightBarRow}>
              <Text variant="caption" color="muted" style={styles.insightBarLabel}>Before</Text>
              <View style={styles.insightBarBg}>
                <View
                  style={[
                    styles.insightBarFill,
                    {
                      width: `${Math.min(100, (insight.before_avg || 0))}%`,
                      backgroundColor: Colors.textMuted,
                    },
                  ]}
                />
              </View>
              <Text variant="caption" color="muted" style={styles.insightBarValue}>
                {insight.before_avg != null ? Math.round(insight.before_avg) : '--'}
              </Text>
            </View>
            <View style={styles.insightBarRow}>
              <Text variant="caption" color="muted" style={styles.insightBarLabel}>After</Text>
              <View style={styles.insightBarBg}>
                <View
                  style={[
                    styles.insightBarFill,
                    {
                      width: `${Math.min(100, (insight.after_avg || 0))}%`,
                      backgroundColor: isPositive ? Colors.success : Colors.error,
                    },
                  ]}
                />
              </View>
              <Text variant="caption" weight="medium" style={[
                styles.insightBarValue,
                { color: isPositive ? Colors.success : Colors.error },
              ]}>
                {insight.after_avg != null ? Math.round(insight.after_avg) : '--'}
              </Text>
            </View>
          </View>
          {mechanism && (
            <Text variant="caption" color="muted" style={styles.mechanismText} numberOfLines={2}>
              {mechanism}
            </Text>
          )}
        </>
      ) : (
        <View style={styles.collectingData}>
          <View style={styles.collectingDot} />
          <Text variant="caption" color="muted">
            Collecting data... ({Math.max(0, 14 - insight.days_on)} more days needed)
          </Text>
        </View>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: Spacing.xxxl + 40,
  },
  header: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.lg,
  },

  // Timeframe
  timeframeContainer: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.lg,
    marginBottom: Spacing.md,
    gap: Spacing.sm,
  },
  timeframeBtn: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.backgroundCard,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  timeframeBtnActive: {
    backgroundColor: Colors.primaryLight,
    borderColor: Colors.primary,
  },

  // Metric selector
  metricSelector: {
    marginBottom: Spacing.md,
  },
  metricSelectorContent: {
    paddingHorizontal: Spacing.lg,
    gap: Spacing.sm,
  },
  metricTab: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.backgroundCard,
  },

  // Averages Card
  averagesCard: {
    marginHorizontal: Spacing.lg,
    marginBottom: Spacing.md,
  },
  sectionLabel: {
    marginBottom: Spacing.md,
  },
  averagesRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  averageItem: {
    alignItems: 'center',
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.md,
    borderRadius: BorderRadius.md,
  },
  dataPoints: {
    marginTop: Spacing.md,
  },

  // Chart
  chartCard: {
    marginHorizontal: Spacing.lg,
    marginBottom: Spacing.lg,
  },
  chartContainer: {
    alignItems: 'center',
    paddingVertical: Spacing.sm,
  },
  chartDateLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: Spacing.xs,
  },

  // Point detail
  pointDetail: {
    marginTop: Spacing.md,
    paddingTop: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  pointDetailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: Spacing.sm,
  },
  pointDetailItem: {
    alignItems: 'center',
    gap: 2,
  },

  // Section headers
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    marginBottom: Spacing.md,
  },
  sectionTitle: {
    marginBottom: Spacing.md,
  },

  // Insights
  insightsSection: {
    marginBottom: Spacing.lg,
  },
  insightCard: {
    marginHorizontal: Spacing.lg,
    marginBottom: Spacing.sm,
  },
  insightHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  insightNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    flex: 1,
  },
  changeBadge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: BorderRadius.full,
  },
  insightMetric: {
    marginBottom: Spacing.sm,
  },
  insightBars: {
    gap: Spacing.xs,
  },
  insightBarRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  insightBarLabel: {
    width: 36,
  },
  insightBarBg: {
    flex: 1,
    height: 6,
    backgroundColor: Colors.border,
    borderRadius: 3,
    overflow: 'hidden',
  },
  insightBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  insightBarValue: {
    width: 28,
    textAlign: 'right',
  },
  mechanismText: {
    marginTop: Spacing.sm,
    lineHeight: 16,
  },
  collectingData: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    marginTop: Spacing.xs,
  },
  collectingDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.warning,
  },

  // Life Events
  lifeEventsSection: {
    marginBottom: Spacing.lg,
  },
  addEventBtn: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    backgroundColor: Colors.primaryLight,
    borderRadius: BorderRadius.full,
  },
  addEventLink: {
    marginTop: Spacing.sm,
  },
  eventsScroll: {
    paddingHorizontal: Spacing.lg,
    gap: Spacing.sm,
  },
  eventChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    backgroundColor: Colors.backgroundCard,
    borderRadius: BorderRadius.md,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    minWidth: 140,
  },
  eventChipIcon: {
    fontSize: 18,
  },

  // Adherence
  adherenceSection: {
    paddingHorizontal: Spacing.lg,
    marginBottom: Spacing.lg,
  },
  adherenceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.03)',
  },
  adherenceInfo: {
    flex: 1,
    marginRight: Spacing.md,
  },
  adherenceBarContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    width: 130,
    gap: Spacing.xs,
  },
  adherenceBarBg: {
    flex: 1,
    height: 4,
    backgroundColor: Colors.border,
    borderRadius: 2,
    overflow: 'hidden',
  },
  adherenceBarFill: {
    height: '100%',
    borderRadius: 2,
  },

  // Supplements
  supplementsSection: {
    paddingHorizontal: Spacing.lg,
    marginBottom: Spacing.lg,
  },
  supplementsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  supplementCard: {
    marginBottom: Spacing.sm,
  },
  supplementRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  supplementInfo: {
    flex: 1,
    gap: Spacing.xs,
  },
  supplementMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  doseBadge: {
    backgroundColor: Colors.primaryLight,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 2,
    borderRadius: BorderRadius.full,
  },
  removeBtn: {
    padding: Spacing.sm,
  },

  // Empty State
  emptyCard: {
    marginHorizontal: Spacing.lg,
    alignItems: 'center',
    paddingVertical: Spacing.xl,
  },
  emptyHint: {
    marginTop: Spacing.sm,
  },

  // Recent Data Table
  recentSection: {
    paddingHorizontal: Spacing.lg,
  },
  tableHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    marginBottom: Spacing.xs,
  },
  tableRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.03)',
  },
  tableDate: {
    flex: 1.3,
  },
  tableScore: {
    flex: 0.8,
    alignItems: 'center',
  },
});
