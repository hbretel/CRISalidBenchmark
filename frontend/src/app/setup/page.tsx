"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { ValidateResponse } from "@/types/api";
import { OpenAlexValidator } from "@/components/setup/OpenAlexValidator";
import { LineageConfirm } from "@/components/setup/LineageConfirm";
import { useConfig } from "@/hooks/useConfig";
import { api, ApiError } from "@/lib/api";
import { CheckCircle, Loader2 } from "lucide-react";

type Step = "validate" | "confirm" | "saving" | "done";

export default function SetupPage() {
  const router = useRouter();
  const { isConfigured } = useConfig();

  // /setup is only ever shown for the very first configuration — once the
  // instance is configured, changes go through /configuration instead.
  useEffect(() => {
    if (isConfigured) router.replace("/");
  }, [isConfigured, router]);

  const [step, setStep] = useState<Step>("validate");
  const [validated, setValidated] = useState<ValidateResponse | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [email, setEmail] = useState("");
  const [institutionName, setInstitutionName] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);

  function handleValidated(data: ValidateResponse, key: string, mail: string) {
    setValidated(data);
    setApiKey(key);
    setEmail(mail);
    setInstitutionName(data.institution_name);
    setStep("confirm");
  }

  async function handleConfirm() {
    if (!validated) return;
    setStep("saving");
    setSaveError(null);
    try {
      await api.post("/config", {
        openalex_institution_id: validated.openalex_institution_id,
        openalex_api_key: apiKey,
        contact_email: email,
        institution_name: institutionName,
      });
      setStep("done");
      setTimeout(() => router.push("/"), 2000);
    } catch (err) {
      setSaveError(
        err instanceof ApiError ? err.detail : "Erreur lors de l'enregistrement.",
      );
      setStep("confirm");
    }
  }

  const stepLabels = ["Saisie", "Périmètre", "Enregistrement"];
  const stepIndex = step === "validate" ? 0 : step === "confirm" ? 1 : 2;

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="w-full max-w-xl bg-white rounded-xl shadow-sm border p-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-xl font-bold text-gray-900">Configuration initiale</h1>
          <p className="text-sm text-gray-500 mt-1">
            Configurez l'établissement à analyser. Cette étape est requise une seule fois.
          </p>
        </div>

        {/* Stepper */}
        <div className="flex gap-0 mb-8">
          {stepLabels.map((label, i) => (
            <div key={label} className="flex-1 flex items-center">
              <div className="flex flex-col items-center flex-1">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-colors ${
                    i < stepIndex
                      ? "bg-brand-600 border-brand-600 text-white"
                      : i === stepIndex
                        ? "border-brand-600 text-brand-600"
                        : "border-gray-300 text-gray-400"
                  }`}
                >
                  {i < stepIndex ? "✓" : i + 1}
                </div>
                <span className={`text-xs mt-1 ${i === stepIndex ? "text-brand-600 font-medium" : "text-gray-400"}`}>
                  {label}
                </span>
              </div>
              {i < stepLabels.length - 1 && (
                <div className={`h-px flex-1 mb-4 mx-1 ${i < stepIndex ? "bg-brand-400" : "bg-gray-200"}`} />
              )}
            </div>
          ))}
        </div>

        {/* Step content */}
        {step === "validate" && (
          <OpenAlexValidator onValidated={handleValidated} />
        )}

        {step === "confirm" && validated && (
          <>
            {saveError && (
              <div className="mb-4 text-sm text-red-600 bg-red-50 p-3 rounded">
                {saveError}
              </div>
            )}
            <LineageConfirm
              data={validated}
              institutionName={institutionName}
              onNameChange={setInstitutionName}
              onConfirm={handleConfirm}
              onBack={() => setStep("validate")}
            />
          </>
        )}

        {step === "saving" && (
          <div className="flex flex-col items-center py-10 gap-3 text-gray-600">
            <Loader2 size={32} className="animate-spin text-brand-600" />
            <span className="text-sm">Enregistrement en cours…</span>
          </div>
        )}

        {step === "done" && (
          <div className="flex flex-col items-center py-10 gap-3 text-green-600">
            <CheckCircle size={40} />
            <span className="text-sm font-medium">Configuration enregistrée.</span>
            <span className="text-xs text-gray-500">Redirection vers le tableau de bord…</span>
          </div>
        )}
      </div>
    </div>
  );
}
