// Country codes (ISO 3166-1 alpha-2) for the account country. The country decides the VAT
// on a plan: EU countries pay their own VAT (OSS), the rest of the world 0%.
export const EU_COUNTRIES: [string, string][] = [
  ['AT', 'Austria'], ['BE', 'Belgium'], ['BG', 'Bulgaria'], ['HR', 'Croatia'], ['CY', 'Cyprus'],
  ['CZ', 'Czechia'], ['DK', 'Denmark'], ['EE', 'Estonia'], ['FI', 'Finland'], ['FR', 'France'],
  ['DE', 'Germany'], ['GR', 'Greece'], ['HU', 'Hungary'], ['IE', 'Ireland'], ['IT', 'Italy'],
  ['LV', 'Latvia'], ['LT', 'Lithuania'], ['LU', 'Luxembourg'], ['MT', 'Malta'], ['NL', 'Netherlands'],
  ['PL', 'Poland'], ['PT', 'Portugal'], ['RO', 'Romania'], ['SK', 'Slovakia'], ['SI', 'Slovenia'],
  ['ES', 'Spain'], ['SE', 'Sweden'],
];

export const OTHER_COUNTRIES: [string, string][] = [
  ['AU', 'Australia'], ['BR', 'Brazil'], ['CA', 'Canada'], ['CN', 'China'], ['EG', 'Egypt'],
  ['ER', 'Eritrea'], ['ET', 'Ethiopia'], ['GH', 'Ghana'], ['HK', 'Hong Kong'], ['IS', 'Iceland'],
  ['IN', 'India'], ['ID', 'Indonesia'], ['IL', 'Israel'], ['JP', 'Japan'], ['KE', 'Kenya'],
  ['MY', 'Malaysia'], ['MX', 'Mexico'], ['MA', 'Morocco'], ['NZ', 'New Zealand'], ['NG', 'Nigeria'],
  ['NO', 'Norway'], ['PK', 'Pakistan'], ['PH', 'Philippines'], ['QA', 'Qatar'], ['SA', 'Saudi Arabia'],
  ['RS', 'Serbia'], ['SG', 'Singapore'], ['ZA', 'South Africa'], ['KR', 'South Korea'], ['CH', 'Switzerland'],
  ['TH', 'Thailand'], ['TR', 'Turkey'], ['UA', 'Ukraine'], ['AE', 'United Arab Emirates'],
  ['GB', 'United Kingdom'], ['US', 'United States'], ['VN', 'Vietnam'],
];

export function CountryOptions() {
  return (
    <>
      <option value="">Select your country…</option>
      <optgroup label="European Union">
        {EU_COUNTRIES.map(([code, name]) => <option key={code} value={code}>{name}</option>)}
      </optgroup>
      <optgroup label="Rest of the world">
        {OTHER_COUNTRIES.map(([code, name]) => <option key={code} value={code}>{name}</option>)}
      </optgroup>
    </>
  );
}
