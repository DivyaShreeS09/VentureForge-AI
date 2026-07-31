import { useNavigate } from "react-router-dom";
import { Button } from "../primitives";

/** Catch-all for any URL that matches no route (typo, stale bookmark, manually edited path).
 * Without this, React Router rendered nothing here — just the ambient background with no
 * content and no way back (found during the pre-submission break-testing pass). */
export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <main className="flex min-h-[100dvh] w-full flex-col items-center justify-center px-6 py-20 text-center font-forge-sans">
      <p className="text-forge-2 text-forge-text-secondary">404</p>
      <h1 className="mt-2 font-forge-serif text-forge-6 font-semibold text-forge-text">Page not found</h1>
      <p className="mt-3 max-w-md text-forge-2 text-forge-text-secondary">
        This link doesn&apos;t match anything in VentureForge AI.
      </p>
      <Button className="mt-8" variant="primary" onClick={() => navigate("/")}>
        Back to start
      </Button>
    </main>
  );
}
