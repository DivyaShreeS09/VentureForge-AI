import { useNavigate } from "react-router-dom";
import { StartupForm, type StartupFormValues } from "../components/venture/StartupForm";
import { VentureEntryPanel } from "../components/venture/VentureEntryPanel";
import { VentureIntroPanel } from "../components/venture/VentureIntroPanel";
import { ErrorBanner } from "../components/status/StatusBanner";
import { useAsync } from "../hooks/useAsync";
import { createStartup } from "../services/api";

export function HomePage() {
  const navigate = useNavigate();
  const { loading, error, run } = useAsync(createStartup);

  async function handleSubmit(values: StartupFormValues) {
    const startup = await run(values);
    if (startup) {
      navigate(`/startups/${startup.id}/status`);
    }
  }

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      <VentureIntroPanel />
      <VentureEntryPanel>
        {error && (
          <div className="mb-6">
            <ErrorBanner message={error} />
          </div>
        )}
        <StartupForm onSubmit={handleSubmit} submitting={loading} />
      </VentureEntryPanel>
    </div>
  );
}
