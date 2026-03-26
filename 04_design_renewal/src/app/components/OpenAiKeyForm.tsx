import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

interface OpenAiKeyFormProps {
  title: string;
  description: string;
  submitLabel: string;
  maskedKey?: string | null;
  onSubmit: (apiKey: string) => Promise<void>;
}

export function OpenAiKeyForm({
  title,
  description,
  submitLabel,
  maskedKey,
  onSubmit,
}: OpenAiKeyFormProps) {
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    const normalized = apiKey.trim();
    if (!normalized.startsWith("sk-")) {
      setError("OpenAI API key 형식이 올바르지 않습니다.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      await onSubmit(normalized);
      setApiKey("");
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "OpenAI key 저장에 실패했습니다.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-[15px] font-semibold text-foreground">{title}</h3>
        <p className="mt-1 text-[13px] text-muted-foreground">{description}</p>
      </div>

      {maskedKey ? (
        <div className="liquid-inline-note rounded-[20px] px-4 py-3">
          <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Connected Key</p>
          <p className="mt-1 font-mono text-[13px] text-foreground">{maskedKey}</p>
        </div>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="openai-api-key">OpenAI API key</Label>
        <Input
          id="openai-api-key"
          name="openaiApiKey"
          type="password"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          placeholder="sk-..."
          autoComplete="off"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
        />
      </div>

      {error ? <p className="text-[12px] text-destructive">{error}</p> : null}

      <Button type="button" onClick={() => void handleSubmit()} className="w-full" disabled={isSubmitting}>
        {isSubmitting ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            저장 중...
          </>
        ) : (
          submitLabel
        )}
      </Button>
    </div>
  );
}
