import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';

type Props = { data: Array<{ date: string; amount: number }>; color?: string };

export default function RevenueChart({ data = [], color = '#0B74FF' }: Props) {
  return (
    <div style={{ width: '100%', height: 240 }} className="card">
      <h3 className="text-sm text-gray-500 mb-2">Revenue (30 days)</h3>
      <ResponsiveContainer>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e6eefc" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis tickFormatter={(v) => `${v}`} />
          <Tooltip formatter={(val: any) => new Intl.NumberFormat().format(Number(val))} />
          <Line type="monotone" dataKey="amount" stroke={color} strokeWidth={3} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
