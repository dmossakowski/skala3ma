import React, {useEffect, useState, useCallback} from 'react';
import {ActivityIndicator, FlatList, SafeAreaView, StyleSheet, Text, View, RefreshControl} from 'react-native';
import {API_BASE} from '../config';

type Gym = {
  id: string;
  name: string;
  homepage?: string;
  address?: string;
};

export default function GymsScreen() {
  const [gyms, setGyms] = useState<Gym[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api1/gyms`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setGyms(Array.isArray(data) ? data : []);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load gyms');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, []);

  if (loading) {
    return (
      <SafeAreaView style={styles.center}> 
        <ActivityIndicator />
        <Text style={styles.muted}>Loading gyms…</Text>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.error}>Error: {error}</Text>
        <Text style={styles.muted}>Ensure Flask is running at {API_BASE}</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <FlatList
        data={gyms}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        renderItem={({item}) => (
          <View style={styles.row}>
            <Text style={styles.name}>{item.name}</Text>
            {item.address ? <Text style={styles.detail}>{item.address}</Text> : null}
            {item.homepage ? <Text style={styles.link}>{item.homepage}</Text> : null}
          </View>
        )}
        ListEmptyComponent={<Text style={styles.muted}>No gyms found.</Text>}
        contentContainerStyle={gyms.length === 0 ? styles.center : undefined}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 16 },
  row: { padding: 16 },
  name: { fontSize: 16, fontWeight: '600', color: '#111827' },
  detail: { fontSize: 14, color: '#374151', marginTop: 2 },
  link: { fontSize: 12, color: '#2563eb', marginTop: 2 },
  separator: { height: 1, backgroundColor: '#e5e7eb' },
  muted: { marginTop: 8, color: '#6b7280' },
  error: { color: '#dc2626', fontWeight: '600' },
});
