import api from "./api";

export type RewardsSummary = {
  balance: number;
  level: string;
  level_min: number;
  next_level_at: number | null;
  catalog: { id: string; title: string; cost: number; blurb: string; redeemable: boolean; reason: string }[];
};

export async function getRewards() {
  const { data } = await api.get<RewardsSummary>("/rewards/me");
  return data;
}
