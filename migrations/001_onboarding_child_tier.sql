ALTER TABLE onboarding_records
    ADD COLUMN IF NOT EXISTS "canFollowSimpleInstruction" BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS "canSpeak" BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS "childTier" VARCHAR;

UPDATE onboarding_records
SET "childTier" = CASE
    WHEN "ageYears" <= 2 THEN 'tier1'
    WHEN "ageYears" <= 4 AND "canFollowSimpleInstruction" THEN 'tier2'
    WHEN "ageYears" <= 4 THEN 'tier1'
    WHEN "canSpeak" THEN 'tier3'
    ELSE 'tier2'
END
WHERE "childTier" IS NULL;

ALTER TABLE onboarding_records
    ALTER COLUMN "childTier" SET NOT NULL;
