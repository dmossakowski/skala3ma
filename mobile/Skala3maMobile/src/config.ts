import {Platform} from 'react-native';

// Android emulator cannot reach 127.0.0.1 on the host directly. Use 10.0.2.2.
// For HTTPS with a self-signed cert on Android, you’ll need to install/trust the cert in the emulator
// or proxy via a trusted cert; so we default to HTTP on Android for dev.
const HOST = Platform.OS === 'android' ? '10.0.2.2' : '127.0.0.1';
const PROTOCOL = 'https';

export const API_BASE = `${PROTOCOL}://${HOST}:3000`;
