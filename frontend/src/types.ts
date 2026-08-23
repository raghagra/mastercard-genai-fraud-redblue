export type AttackCard = {
  attack_id: string; bucket: string; subtype: string; attack_name: string;
  variant_name: string; channel: string; rail: string; scope: string; severity: string;
};

export type Iteration = {
  iteration_id: string; seed: number; counts: Record<string, number>;
  evaluation_overall: Record<string, number>; failure_summary: Record<string, number>;
};

export type Provider = {
  label: string; type: string; fields: string[]; secret_fields: string[]; credential_note?: string;
};
