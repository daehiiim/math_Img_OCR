import type { ComponentType } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Label } from "../ui/label";
import { RadioGroup, RadioGroupItem } from "../ui/radio-group";

interface PaymentMethodOption {
  id: string;
  label: string;
  sublabel?: string;
  icon: ComponentType<{ className?: string }>;
}

interface PaymentMethodSelectorProps {
  value: string;
  options: PaymentMethodOption[];
  disabled?: boolean;
  description?: string;
  onValueChange: (value: string) => void;
}

/** 결제 수단 라디오 리스트를 접근성 있는 shadcn 조합으로 렌더링한다. */
export function PaymentMethodSelector({
  value,
  options,
  disabled,
  description,
  onValueChange,
}: PaymentMethodSelectorProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>결제 수단</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        <RadioGroup value={value} onValueChange={onValueChange}>
          {options.map((option) => <PaymentMethodRow key={option.id} option={option} checked={option.id === value} disabled={disabled} />)}
        </RadioGroup>
      </CardContent>
    </Card>
  );
}

/** 결제 수단 하나를 라디오 아이템과 보조 설명으로 표시한다. */
function PaymentMethodRow({
  option,
  checked,
  disabled,
}: {
  option: PaymentMethodOption;
  checked: boolean;
  disabled?: boolean;
}) {
  const Icon = option.icon;

  return (
    <Label htmlFor={option.id} className="flex items-center gap-3 rounded-xl border p-4">
      <RadioGroupItem id={option.id} value={option.id} disabled={disabled} />
      <Icon className={checked ? "text-foreground" : "text-muted-foreground"} />
      <div className="flex-1"><p>{option.label}</p>{option.sublabel ? <p className="text-xs text-muted-foreground">{option.sublabel}</p> : null}</div>
    </Label>
  );
}
