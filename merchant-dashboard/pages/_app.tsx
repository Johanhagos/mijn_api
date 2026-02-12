import '../styles/globals.css';
import type { AppProps } from 'next/app';
import Header from '../components/Header';

// Force rebuild: API_BASE fix deployment 2026-02-12
export default function MyApp({ Component, pageProps }: AppProps) {
  return (
    <>
      <Header />
      <Component {...pageProps} />
    </>
  );
}
