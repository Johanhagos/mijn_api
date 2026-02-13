import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import api from '../lib/api';

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const devBypass = process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === 'true';

  useEffect(() => {
    if (devBypass) {
      setLoading(false);
      return;
    }
    let mounted = true;
    (async () => {
      try {
        // Try a simple authenticated call; protectedApi will attempt refresh if needed
        await api.protectedApi('/merchant/usage');
        if (mounted) setLoading(false);
      } catch (err) {
        // If unauthorized, protectedApi already redirects on 401, but ensure router replacement
        if (mounted) router.replace('/login');
      }
    })();
    return () => { mounted = false; };
  }, [router]);

  if (loading) return <div className="p-8">Checking authentication…</div>;
  if (devBypass) {
    return (
      <>
        <div className="bg-amber-600 text-white text-xs px-3 py-1 text-center">
          Dev auth bypass enabled
        </div>
        {children}
      </>
    );
  }
  return <>{children}</>;
}
