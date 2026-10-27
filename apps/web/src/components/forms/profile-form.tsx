"use client";

import { PROFILE_LIMITS, SEARCH_TYPES } from "@kandid/core/profile/constants";
import { useActionState } from "react";
import { Button } from "@/components/ui/button";
import { describedBy, Field } from "@/components/ui/field";
import { Input, Select } from "@/components/ui/input";
import { type FormState, initialFormState } from "@/lib/form";
import { SEARCH_TYPE_LABELS } from "@/lib/labels";

const RHYTHM_HINT = "Par exemple : 3 semaines en entreprise, 1 semaine à l'école.";

type ProfileFormProps = {
  action: (state: FormState, formData: FormData) => Promise<FormState>;
  defaultValues?: Record<string, string>;
  submitLabel: string;
};

export function ProfileForm({ action, defaultValues = {}, submitLabel }: ProfileFormProps) {
  const [state, formAction, pending] = useActionState(action, initialFormState);
  const values = state.values ?? defaultValues;
  const errors = state.fieldErrors ?? {};

  return (
    <form action={formAction} className="flex flex-col gap-5" noValidate>
      <Field id="firstName" label="Prénom" error={errors.firstName}>
        <Input
          id="firstName"
          name="firstName"
          autoComplete="given-name"
          required
          maxLength={PROFILE_LIMITS.firstName}
          defaultValue={values.firstName}
          {...describedBy("firstName", { error: errors.firstName })}
        />
      </Field>

      <Field id="searchType" label="Ce que tu cherches" error={errors.searchType}>
        <Select
          id="searchType"
          name="searchType"
          defaultValue={values.searchType ?? "work_study"}
          {...describedBy("searchType", { error: errors.searchType })}
        >
          {SEARCH_TYPES.map((type) => (
            <option key={type} value={type}>
              {SEARCH_TYPE_LABELS[type]}
            </option>
          ))}
        </Select>
      </Field>

      <Field id="school" label="École ou formation (facultatif)" error={errors.school}>
        <Input
          id="school"
          name="school"
          maxLength={PROFILE_LIMITS.school}
          defaultValue={values.school}
          {...describedBy("school", { error: errors.school })}
        />
      </Field>

      <Field id="startDate" label="Date de début souhaitée (facultatif)" error={errors.startDate}>
        <Input
          id="startDate"
          name="startDate"
          type="date"
          defaultValue={values.startDate}
          {...describedBy("startDate", { error: errors.startDate })}
        />
      </Field>

      <Field
        id="workStudyRhythm"
        label="Rythme d'alternance (facultatif)"
        hint={RHYTHM_HINT}
        error={errors.workStudyRhythm}
      >
        <Input
          id="workStudyRhythm"
          name="workStudyRhythm"
          maxLength={PROFILE_LIMITS.workStudyRhythm}
          defaultValue={values.workStudyRhythm}
          {...describedBy("workStudyRhythm", { hint: RHYTHM_HINT, error: errors.workStudyRhythm })}
        />
      </Field>

      {state.message && (
        <p
          role={state.status === "error" ? "alert" : "status"}
          className={state.status === "error" ? "text-destructive" : "text-primary"}
        >
          {state.message}
        </p>
      )}

      <Button type="submit" disabled={pending} className="self-start">
        {pending ? "Enregistrement..." : submitLabel}
      </Button>
    </form>
  );
}
