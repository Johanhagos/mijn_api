import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import api from '../lib/api';
import { DEV_BYPASS_AUTH } from '../lib/config';

// requirePlan={false}: pages a merchant needs before buying a plan (e.g. account settings)
export default function AuthGuard({ children, requirePlan = true }: { children: React.ReactNode; requirePlan?: boolean }) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const devBypass = DEV_BYPASS_AUTH;

  useEffect(() => {
    if (devBypass) {
      setLoading(false);
      return;
    }
    let mounted = true;
    (async () => {
      try {
        // Authenticated call (protectedApi refreshes the token if needed). The dashboard
        // is only for merchants with a paid plan; the backend enforces this as well.
        const me = await api.protectedApi('/merchant/me');
        if (!mounted) return;
        if (requirePlan && !me?.plan_active) {
          router.replace('/plans');
          return;
        }
        setLoading(false);
      } catch (err) {
        // If unauthorized, protectedApi already redirects on 401, but ensure router replacement
        if (mounted) router.replace('/login');
      }
    })();
    return () => { mounted = false; };
  }, [router, requirePlan]);

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
