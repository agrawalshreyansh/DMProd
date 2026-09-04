import { render, screen } from "@testing-library/react";
import BreakdownBars from "@/components/BreakdownBars";

test("shows an empty state with no items", () => {
  render(<BreakdownBars items={[]} />);
  expect(screen.getByText(/no data yet/i)).toBeInTheDocument();
});

test("renders a label and count per item, using the labels map when provided", () => {
  render(
    <BreakdownBars
      items={[
        { label: "action_item", count: 4 },
        { label: "other", count: 1 },
      ]}
      labels={{ action_item: "Action item" }}
    />,
  );

  expect(screen.getByText("Action item")).toBeInTheDocument();
  expect(screen.getByText("4")).toBeInTheDocument();
  // Falls back to the raw label when nothing in the map matches.
  expect(screen.getByText("other")).toBeInTheDocument();
  expect(screen.getByText("1")).toBeInTheDocument();
});
