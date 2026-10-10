import { Package } from "lucide-react";
import { HOUSEHOLD_CATEGORIES } from "../../constants/donations";
import { DonationCategory } from "../../types/models";

export function CategoryTiles({
  selected,
  onSelect,
}: {
  selected?: DonationCategory | null;
  onSelect: (id: DonationCategory) => void;
}) {
  return (
    <div className="category-grid">
      {HOUSEHOLD_CATEGORIES.map((cat) => (
        <button
          key={cat.id}
          type="button"
          className={`category-tile ${selected === cat.id ? "is-on" : ""}`}
          onClick={() => onSelect(cat.id)}
        >
          <div className={`category-visual tint-${cat.tint}`}>
            {cat.image ? <img src={cat.image} alt="" /> : <Package size={28} />}
          </div>
          <div className="category-copy">
            <strong>{cat.label}</strong>
            <span>{cat.hint}</span>
          </div>
        </button>
      ))}
    </div>
  );
}
