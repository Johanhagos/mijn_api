import React from 'react';
import { LucideKey } from 'lucide-react';

type KeyItem = { id: string | number; key_type: string; masked: string; created_at: string };

export default function ApiKeysList({ keys = [], onRevoke }: { keys?: KeyItem[]; onRevoke?: (id: any) => void }) {
  return (
    <div className="card">
      <h3 className="text-sm text-gray-500 mb-3">Active API Keys</h3>
      <div className="space-y-3">
        {keys.length === 0 ? (
          <div className="text-sm text-gray-500">No keys yet.</div>
        ) : (
          keys.map((k) => (
            <div key={k.id} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="badge badge-live"><LucideKey size={14} /></span>
                <div>
                  <div className="font-mono text-sm">{k.masked}</div>
                  <div className="text-xs text-gray-500">Created {k.created_at}</div>
                </div>
              </div>
              <div>
                <button className="btn btn-ghost text-sm text-red-600" onClick={() => onRevoke?.(k.id)}>Revoke</button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
