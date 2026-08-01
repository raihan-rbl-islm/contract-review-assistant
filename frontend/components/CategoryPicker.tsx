"use client";

interface CategoryPickerProps {
  categories: string[];
  selectedCategory: string;
  onSelect: (category: string) => void;
}

export default function CategoryPicker({
  categories,
  selectedCategory,
  onSelect,
}: CategoryPickerProps) {
  return (
    <div className="category-picker">
      <label className="picker-label">Clause Category</label>
      <div className="category-grid">
        {categories.map((cat) => (
          <button
            key={cat}
            className={`category-chip ${selectedCategory === cat ? "selected" : ""}`}
            onClick={() => onSelect(cat)}
            type="button"
          >
            {cat}
          </button>
        ))}
      </div>
    </div>
  );
}
