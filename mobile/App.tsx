import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect } from 'react';
import { Text } from 'react-native';
import { MD3DarkTheme, PaperProvider } from 'react-native-paper';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { apiRequest, getToken } from './src/api/client';
import LibraryScreen from './src/screens/LibraryScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import RenderScreen from './src/screens/RenderScreen';
import UploadScreen from './src/screens/UploadScreen';
import { useAuthStore } from './src/store/authStore';
import { Colors } from './src/theme/colors';

const Tab = createBottomTabNavigator();

const paperTheme = {
  ...MD3DarkTheme,
  colors: {
    ...MD3DarkTheme.colors,
    primary: Colors.primary,
    background: Colors.bg,
    surface: Colors.surface,
  },
};

export default function App() {
  const { setUser, setHydrated } = useAuthStore();

  // Restore session on app start
  useEffect(() => {
    (async () => {
      try {
        const token = await getToken();
        if (token) {
          const res = await apiRequest<{ authenticated: boolean; user: { id: string; username: string; role: string } | null }>(
            '/api/auth/me'
          );
          if (res.authenticated && res.user) {
            setUser(res.user);
          }
        }
      } catch {
        // Token invalid or server unreachable — stay logged out
      } finally {
        setHydrated(true);
      }
    })();
  }, []);

  return (
    <SafeAreaProvider>
      <PaperProvider theme={paperTheme}>
        <NavigationContainer>
          <StatusBar style="light" />
          <Tab.Navigator
            screenOptions={{
              headerStyle: { backgroundColor: Colors.surface },
              headerTintColor: Colors.text,
              headerShadowVisible: false,
              tabBarStyle: {
                backgroundColor: Colors.surface,
                borderTopColor: Colors.border,
                borderTopWidth: 1,
              },
              tabBarActiveTintColor: Colors.primary,
              tabBarInactiveTintColor: Colors.muted,
              tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
            }}
          >
            <Tab.Screen
              name="Upload"
              component={UploadScreen}
              options={{
                title: 'Upload Clips',
                tabBarLabel: 'Upload',
                tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>🎬</Text>,
              }}
            />
            <Tab.Screen
              name="Render"
              component={RenderScreen}
              options={{
                title: 'Render',
                tabBarLabel: 'Render',
                tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>✨</Text>,
              }}
            />
            <Tab.Screen
              name="Library"
              component={LibraryScreen}
              options={{
                title: 'Library',
                tabBarLabel: 'Library',
                tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>📁</Text>,
              }}
            />
            <Tab.Screen
              name="Profile"
              component={ProfileScreen}
              options={{
                title: 'Profile',
                tabBarLabel: 'Profile',
                tabBarIcon: ({ color }) => <Text style={{ color, fontSize: 20 }}>👤</Text>,
              }}
            />
          </Tab.Navigator>
        </NavigationContainer>
      </PaperProvider>
    </SafeAreaProvider>
  );
}
