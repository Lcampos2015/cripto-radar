// Cripto Radar IA - disparador puntual de GitHub Actions (Cloudflare Workers + Cron Triggers).
//
// Por que existe: GitHub atrasa o saltea sus propios cron. El 2026-10-03 corrio el radar
// cada 4-5 horas (programado cada 30 min) y directamente salteo el briefing de las 19:05.
// Este Worker le dice a GitHub "corre ahora" en el minuto exacto.
//
// No toca datos ni secretos del radar: SOLO lanza workflows. Todo lo demas sigue en GitHub.
// Secret requerido en Cloudflare: GITHUB_TOKEN (fine-grained, solo el repo cripto-radar,
// unico permiso: Actions read and write; con fecha de vencimiento).
//
// Los Cron Triggers de Cloudflare tienen que ser EXACTAMENTE estas expresiones (en UTC):

const REPO = "Lcampos2015/cripto-radar";
const WORKFLOWS = {
  "5 0 * * *": "briefing.yml",    // 00:05 UTC = 19:05 Peru, apenas cierra la vela diaria
  "7,37 * * * *": "radar.yml",    // monitor + eventos fuertes, cada 30 min
};

export default {
  async scheduled(event, env, ctx) {
    const workflow = WORKFLOWS[event.cron];
    if (!workflow) {
      console.log(`Cron sin workflow asignado: "${event.cron}" (revisar que coincida exacto con WORKFLOWS)`);
      return;
    }
    const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${workflow}/dispatches`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "cripto-radar-cloudflare",   // GitHub rechaza pedidos sin User-Agent
      },
      body: JSON.stringify({ ref: "main" }),
    });
    // 204 = GitHub acepto la orden. Cualquier otra cosa queda en los logs del Worker.
    if (r.status === 204) {
      console.log(`${workflow}: lanzado (204)`);
    } else {
      const detalle = (await r.text()).slice(0, 200);
      console.log(`${workflow}: GitHub respondio ${r.status}: ${detalle}`);
      throw new Error(`GitHub respondio ${r.status} para ${workflow}`);
    }
  },
};
