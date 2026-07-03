import { expect, test } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const fixture = path.resolve(__dirname, '../../../../packages/fixtures/real/phase7/round-01.png');

async function pasteImage(page: import('@playwright/test').Page, filePath: string) {
  const base64 = fs.readFileSync(filePath).toString('base64');
  await page.evaluate(value => {
    const bytes = Uint8Array.from(atob(value), character => character.charCodeAt(0));
    const transfer = new DataTransfer();
    transfer.items.add(new File([bytes], 'capture.png', { type: 'image/png' }));
    window.dispatchEvent(new ClipboardEvent('paste', { clipboardData: transfer, bubbles: true }));
  }, base64);
}

test('Ctrl+V runs recognition and solver without normal manual controls', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Choisir la fenêtre Dofus' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Capturer ce tour' })).toBeDisabled();
  await expect(page.getByText('© 2026 Pawmi (Sinaninho)', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Capture d’écran du début du tour' })).toBeVisible();
  await pasteImage(page, fixture);

  await expect(page.getByRole('heading', { name: /Actions à exécuter|Aucun coup sûr|Nouvelle capture nécessaire/ })).toBeVisible({ timeout: 5_000 });
  await expect(page.getByTestId('action-target-marker').first()).toBeVisible();
  await expect(page.getByTestId('final-cell-marker')).toBeVisible();
  await expect(page.locator('.overlay-legend')).toBeVisible();
  await expect(page.locator('.movement-line').first()).toBeVisible();

  const actionNumbers = page.getByTestId('action-number');
  const actionCount = await actionNumbers.count();
  expect(actionCount).toBeGreaterThan(0);
  expect(await actionNumbers.allTextContents()).toEqual(
    Array.from({ length: actionCount }, (_value, index) => String(index + 1)),
  );
  await expect(page.getByText('Charges : maintenant → prochain tour', { exact: true })).toBeVisible();
  await expect(page.locator('.charges')).toContainText('Indécision 2 →');

  const standardText = await page.locator('body').innerText();
  expect(standardText).not.toContain('Autres options équivalentes');
  for (const forbidden of ['Calculer le tour', 'Budget d’actions', 'Confirmer tous les piliers', 'Confirmer le motif affiché', 'Réflexion', 'Répulsion', 'Attirance']) {
    expect(standardText).not.toContain(forbidden);
  }
});

test('player-facing spell labels use the binding names in Debug mode', async ({ page }) => {
  await page.goto('/?debug=1');
  await page.getByLabel('Capture du combat (debug)').setInputFiles(fixture);
  for (const spell of ['Indécision', 'Reflet', 'Rejet', 'Attrait']) {
    await expect(page.getByText(spell, { exact: true }).first()).toBeVisible();
  }
});
