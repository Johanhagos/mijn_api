import React from 'react';
import { useState } from 'react';

export default function PluginSetup({ snippet }: { snippet?: string }) {
  const [copied, setCopied] = useState(false);
  const code = snippet || `<script src=\"https://example.com/plugin.js\"></script>`;
  return (
    <div className="card">
      <h3 className="text-sm text-gray-500 mb-3">Plugin Setup</h3>
      <pre className="p-3 bg-gray-50 rounded text-xs overflow-auto">{code}</pre>
      <div className="mt-3">
        <button
          className="btn btn-primary"
          onClick={() => {
            navigator.clipboard?.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
          }}
        >
          {copied ? 'Copied' : 'Copy Embed Snippet'}
        </button>
      </div>
    </div>
  );
}
