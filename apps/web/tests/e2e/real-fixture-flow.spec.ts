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
  await expect(page.getByRole('heading', { name: 'Collez la capture avec Ctrl+V' })).toBeVisible();
  await pasteImage(page, fixture);

  await expect(page.getByTestId('player-overlay')).toBeVisible({ timeout: 5_000 });
  await expect(page.getByTestId('pillar-overlay')).toHaveCount(24);
  await expect(page.getByText(/Votre tour est prêt|Aucun déplacement sûr trouvé|Une vérification reste nécessaire/)).toBeVisible({ timeout: 5_000 });

  const standardText = await page.locator('body').innerText();
  for (const forbidden of ['Calculer le tour', 'Budget d’actions', 'Confirmer tous les piliers', 'Confirmer le motif affiché', 'Réflexion', 'Répulsion', 'Attirance']) {
    expect(standardText).not.toContain(forbidden);
  }
});

test('player-facing spell labels use the binding names in Debug mode', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Debug' }).click();
  await page.getByLabel('Capture du combat (debug)').setInputFiles(fixture);
  for (const spell of ['Indécision', 'Reflet', 'Rejet', 'Attrait']) {
    await expect(page.getByText(spell, { exact: true }).first()).toBeVisible();
  }
});
