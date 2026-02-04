import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

type Props = { data: Array<{ name: string; value: number }>; colors?: string[] };

export default function PaymentDonut({ data = [], colors = ['#0B74FF', '#7C3AED'] }: Props) {
  return (
    <div style={{ width: '100%', height: 240 }} className="card">
      <h3 className="text-sm text-gray-500 mb-2">Payment Split</h3>
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={60} outerRadius={80} paddingAngle={4}>
            {data.map((_, i) => (
              <Cell key={`cell-${i}`} fill={colors[i % colors.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
