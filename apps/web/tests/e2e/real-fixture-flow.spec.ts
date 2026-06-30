import { expect, test } from '@playwright/test';
import path from 'node:path';

const fixture = path.resolve(__dirname, '../../../../packages/fixtures/real/phase7/round-01.png');
const emptyArena = path.resolve(__dirname, '../../../../assets/reference/empty_arena.jpeg');

test('real screenshot reaches a player-facing recommendation', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Grougalorasalar Solver' })).toBeVisible();

  const uploadStarted = Date.now();
  await page.getByLabel('Capture du combat').setInputFiles(fixture);
  await expect(page.getByText('Éléments détectés — vérification requise')).toBeVisible({ timeout: 5_000 });
  expect(Date.now() - uploadStarted).toBeLessThan(5_000);

  await expect(page.getByTestId('player-overlay')).toBeVisible();
  await expect(page.getByTestId('pillar-overlay')).toHaveCount(24);
  await expect(page.getByTestId('glyph-overlay')).toHaveCount(6);
  await expect(page.getByText('Joueur détecté')).toBeVisible();
  await expect(page.getByText('24 piliers proposés')).toBeVisible();
  await expect(page.getByText('6 cases du motif')).toBeVisible();

  const standardText = await page.locator('body').innerText();
  for (const forbidden of ['blocked_unverified_rule', 'rules_blocked', 'server_fast_fallback', 'stateVersion', 'S-BLOCK-']) {
    expect(standardText).not.toContain(forbidden);
  }

  const calculate = page.getByRole('button', { name: 'Calculer le tour' });
  await expect(calculate).toBeDisabled();

  await page.getByLabel('J’ai vérifié toute la liste sur l’image.').check();
  await page.getByRole('button', { name: 'Confirmer tous les piliers' }).click();
  await expect(page.getByRole('button', { name: '✓ Piliers confirmés' })).toBeVisible();

  await page.getByRole('button', { name: 'Confirmer le motif affiché' }).click();
  await expect(page.getByRole('button', { name: '✓ Motif confirmé' })).toBeVisible();

  const budgetOne = page.getByRole('group', { name: 'Budget d’actions' }).getByRole('button', { name: '1', exact: true });
  await budgetOne.click();
  await expect(budgetOne).toHaveClass(/selected/);
  for (const spell of ['Indécision', 'Réflexion', 'Répulsion', 'Attirance']) {
    const available = page.getByRole('group', { name: `État de ${spell}` }).getByRole('button', { name: 'Disponible', exact: true });
    await available.click();
    await expect(available).toHaveClass(/selected/);
  }
  await page.getByRole('button', { name: 'Valider les éléments détectés' }).click();
  await expect(page.getByRole('button', { name: '✓ Détections vérifiées' })).toBeVisible();

  await expect(page.getByText('Joueur reconnu')).toBeVisible();
  await expect(page.getByText('Piliers complets')).toBeVisible();
  await expect(page.getByText('Motif reconnu')).toBeVisible();
  await expect(page.getByText('Budget d’actions connu')).toBeVisible();
  await expect(page.getByText('État des sorts connu')).toBeVisible();
  await expect(calculate).toBeEnabled();

  await calculate.click();
  await expect(page.getByText(/Votre tour est prêt|Aucun déplacement sûr trouvé/)).toBeVisible();
  const result = await page.locator('.result').innerText();
  expect(result).not.toContain('blocked_unverified_rule');
  expect(result).not.toContain('S-BLOCK-');
});

test('glyph failure has an explicit message and click correction control', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Capture du combat').setInputFiles(emptyArena);
  await expect(page.getByText('Le motif central n’a pas été détecté.', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ajouter une case sombre' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Ajouter une case claire' })).toBeVisible();
});
