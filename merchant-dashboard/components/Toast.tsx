import React from 'react';

type Props = {
  open: boolean;
  message?: string;
};

export default function Toast({ open, message }: Props) {
  if (!open) return null;
  return (
    <div className="fixed right-6 bottom-6 z-50">
      <div className="bg-gray-900 text-white px-4 py-2 rounded shadow-lg">{message}</div>
    </div>
  );
}
