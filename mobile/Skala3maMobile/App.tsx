/**
 * Sample React Native App
 * https://github.com/facebook/react-native
 *
 * @format
 */

import React, {useEffect, useState} from 'react';
import {SafeAreaView, StatusBar, StyleSheet, Text, View, Pressable, Alert} from 'react-native';
import { GoogleSignin, statusCodes, type User, type SignInResponse } from '@react-native-google-signin/google-signin';
import { GOOGLE_WEB_CLIENT_ID } from './src/config/auth';
import {NavigationContainer} from '@react-navigation/native';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import GymsScreen from './src/screens/GymsScreen';

type RootStackParamList = {
  Home: undefined;
  Gyms: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

function HomeScreen({navigation}: any) {
  const [userInfo, setUserInfo] = useState<User | null>(null);

  useEffect(() => {
    GoogleSignin.configure({
      webClientId: GOOGLE_WEB_CLIENT_ID || undefined,
      offlineAccess: false,
      forceCodeForRefreshToken: false,
      scopes: ['profile', 'email'],
    });
  }, []);

  const handleGoogleSignIn = async () => {
    try {
      const hasPlay = await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
      if (!hasPlay) {
        Alert.alert('Google Play Services', 'Google Play Services not available or outdated.');
        return;
      }

      const resp: SignInResponse = await GoogleSignin.signIn();
      if (resp.type === 'success') {
        const data = resp.data;
        setUserInfo(data);
        const idToken = data.idToken;
        const email = data.user?.email;
        Alert.alert('Signed in', email ? `Welcome ${email}` : 'Google sign-in succeeded');
        // TODO: Send idToken to your backend for verification and session exchange if needed.
      } else if (resp.type === 'cancelled') {
        // User cancelled; no-op
        return;
      }
    } catch (error: any) {
      if (error.code === statusCodes.SIGN_IN_CANCELLED) {
        // user cancelled the login flow
        return;
      } else if (error.code === statusCodes.IN_PROGRESS) {
        Alert.alert('Google Sign-In', 'Sign-in already in progress.');
      } else if (error.code === statusCodes.PLAY_SERVICES_NOT_AVAILABLE) {
        Alert.alert('Google Sign-In', 'Play services not available or outdated.');
      } else {
        Alert.alert('Google Sign-In Error', error?.message || 'Unknown error');
      }
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <View style={styles.card}>
        <Text style={styles.title}>Skala3ma Mobile</Text>
        <Text style={styles.subtitle}>React Native is running ✅</Text>
        <View style={styles.buttonsRow}>
          <Pressable style={styles.button} onPress={() => navigation.navigate('Gyms')}>
            <Text style={styles.buttonText}>View Gyms</Text>
          </Pressable>
          <Pressable style={[styles.button, styles.googleButton]} onPress={handleGoogleSignIn}>
            <Text style={[styles.buttonText, styles.googleButtonText]}>Sign in with Google</Text>
          </Pressable>
        </View>
        {userInfo?.user?.email ? (
          <Text style={styles.signedInText}>Signed in as {userInfo.user.email}</Text>
        ) : null}
      </View>
    </SafeAreaView>
  );
}

function App(): React.JSX.Element {
  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="Gyms" component={GymsScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#f5f6fa',
  },
  card: {
    padding: 24,
    borderRadius: 12,
    backgroundColor: '#ffffff',
    shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowRadius: 8,
    shadowOffset: {width: 0, height: 4},
    elevation: 2,
    alignItems: 'center',
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 16,
    color: '#4b5563',
  },
  button: {
    marginTop: 16,
    backgroundColor: '#2563eb',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  buttonText: { color: 'white', fontWeight: '600' },
  buttonsRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  googleButton: {
    backgroundColor: '#ffffff',
    borderWidth: 1,
    borderColor: '#d1d5db',
    marginLeft: 12,
  },
  googleButtonText: {
    color: '#111827',
  },
  signedInText: {
    marginTop: 12,
    color: '#065f46',
    fontWeight: '500',
  },
});

export default App;
