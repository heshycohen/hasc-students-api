/**
 * Medical due date filter: pass if record's medical_due_date matches the filter option.
 * @param {{ medical_due_date: string | null }} record - Record with medical_due_date (YYYY-MM-DD)
 * @param {string} filterValue - '', 'due', '1month', '2months', '3months'
 * @returns {boolean}
 */
export function passesMedicalDueFilter(record, filterValue) {
  if (!filterValue) return true;
  const dueStr = record.medical_due_date;
  if (!dueStr) return false;
  const due = new Date(dueStr);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dueOnly = new Date(due.getFullYear(), due.getMonth(), due.getDate());

  if (filterValue === 'due') return dueOnly <= today;

  const addMonths = (d, m) => {
    const x = new Date(d);
    x.setMonth(x.getMonth() + m);
    return x;
  };
  if (filterValue === '1month') {
    const end = addMonths(today, 1);
    return dueOnly > today && dueOnly <= end;
  }
  if (filterValue === '2months') {
    const end = addMonths(today, 2);
    return dueOnly > today && dueOnly <= end;
  }
  if (filterValue === '3months') {
    const end = addMonths(today, 3);
    return dueOnly > today && dueOnly <= end;
  }
  return true;
}

export const MEDICAL_DUE_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'due', label: 'Medical due' },
  { value: '1month', label: 'Within 1 month' },
  { value: '2months', label: 'Within 2 months' },
  { value: '3months', label: 'Within 3 months' },
];
