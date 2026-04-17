import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import DomainFilter from "@/components/DomainFilter";
import type { DomainKey } from "@/lib/explore/urlState";

afterEach(() => {
  cleanup();
});

describe("DomainFilter", () => {
  const allDomains: DomainKey[] = ["uspstf", "acc-aha", "kdigo"];

  it("renders all three domain chips", () => {
    const onChange = vi.fn();
    render(<DomainFilter visibleDomains={allDomains} onChange={onChange} />);

    expect(screen.getByTestId("domain-chip-uspstf")).toBeDefined();
    expect(screen.getByTestId("domain-chip-acc-aha")).toBeDefined();
    expect(screen.getByTestId("domain-chip-kdigo")).toBeDefined();
  });

  it("marks active domains as checked", () => {
    const onChange = vi.fn();
    render(<DomainFilter visibleDomains={["uspstf"]} onChange={onChange} />);

    expect(screen.getByTestId("domain-chip-uspstf").getAttribute("aria-checked")).toBe("true");
    expect(screen.getByTestId("domain-chip-acc-aha").getAttribute("aria-checked")).toBe("false");
    expect(screen.getByTestId("domain-chip-kdigo").getAttribute("aria-checked")).toBe("false");
  });

  it("toggles a domain off when clicked", () => {
    const onChange = vi.fn();
    render(<DomainFilter visibleDomains={allDomains} onChange={onChange} />);

    fireEvent.click(screen.getByTestId("domain-chip-kdigo"));
    expect(onChange).toHaveBeenCalledWith(["uspstf", "acc-aha"]);
  });

  it("toggles a domain on when clicked", () => {
    const onChange = vi.fn();
    render(<DomainFilter visibleDomains={["uspstf"]} onChange={onChange} />);

    fireEvent.click(screen.getByTestId("domain-chip-acc-aha"));
    expect(onChange).toHaveBeenCalledWith(["uspstf", "acc-aha"]);
  });

  it("has proper accessibility role", () => {
    const onChange = vi.fn();
    render(<DomainFilter visibleDomains={allDomains} onChange={onChange} />);

    const group = screen.getByRole("group");
    expect(group.getAttribute("aria-label")).toBe("Guideline domain filter");
  });
});
