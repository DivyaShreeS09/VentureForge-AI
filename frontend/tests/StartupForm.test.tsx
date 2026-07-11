import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StartupForm } from "../src/components/venture/StartupForm";

describe("StartupForm", () => {
  it("shows a validation error and does not submit when name is missing", () => {
    const onSubmit = vi.fn();
    render(<StartupForm onSubmit={onSubmit} submitting={false} />);

    fireEvent.change(screen.getByLabelText(/startup description/i), {
      target: { value: "A long enough description of the idea." },
    });
    fireEvent.click(screen.getByRole("button", { name: /initiate venture analysis/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/name is required/i);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows a validation error when description is too short", () => {
    const onSubmit = vi.fn();
    render(<StartupForm onSubmit={onSubmit} submitting={false} />);

    fireEvent.change(screen.getByLabelText(/startup name/i), { target: { value: "Nova" } });
    fireEvent.change(screen.getByLabelText(/startup description/i), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: /initiate venture analysis/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/at least 10 characters/i);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits with name, description, and funding answers", () => {
    const onSubmit = vi.fn();
    render(<StartupForm onSubmit={onSubmit} submitting={false} />);

    fireEvent.change(screen.getByLabelText(/startup name/i), { target: { value: "Nova" } });
    fireEvent.change(screen.getByLabelText(/startup description/i), {
      target: { value: "A subscription analytics dashboard for retail teams." },
    });
    fireEvent.change(screen.getByLabelText(/problem clarity/i), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: /initiate venture analysis/i }));

    expect(onSubmit).toHaveBeenCalledWith({
      name: "Nova",
      description: "A subscription analytics dashboard for retail teams.",
      funding_answers: expect.objectContaining({ problem_clarity: 2 }),
    });
  });

  it("disables the submit button while submitting", () => {
    render(<StartupForm onSubmit={vi.fn()} submitting={true} />);
    expect(screen.getByRole("button", { name: /submitting/i })).toBeDisabled();
  });

  it("exposes submission completeness as an accessible progressbar that updates with input", () => {
    render(<StartupForm onSubmit={vi.fn()} submitting={false} />);

    const progress = screen.getByRole("progressbar", { name: /submission completeness/i });
    expect(progress).toHaveAttribute("aria-valuenow", "0");

    fireEvent.change(screen.getByLabelText(/startup name/i), { target: { value: "Nova" } });
    expect(progress.getAttribute("aria-valuenow")).not.toBe("0");
  });
});
