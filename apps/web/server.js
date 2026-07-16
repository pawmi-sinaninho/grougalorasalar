const http = require('http');
const next = require('next');

const publicBasePath =
  process.env.NEXT_PUBLIC_BASE_PATH || '/grougalorasalar';

const internalMountPath =
  process.env.INTERNAL_MOUNT_PATH || '/solver/grougalorasalar';

const rawPort = process.env.PORT;

const listenTarget =
  rawPort && /^[0-9]+$/.test(rawPort)
    ? Number(rawPort)
    : rawPort || 3000;

const app = next({
  dev: false,
  dir: __dirname,
});

const handle = app.getRequestHandler();

function normalizeRequestUrl(rawUrl) {
  const parsed = new URL(rawUrl || '/', 'http://localhost');
  let pathname = parsed.pathname;

  if (
    pathname === internalMountPath ||
    pathname.startsWith(`${internalMountPath}/`)
  ) {
    pathname = pathname.slice(internalMountPath.length) || '/';
  }

  if (
    pathname !== publicBasePath &&
    !pathname.startsWith(`${publicBasePath}/`)
  ) {
    pathname =
      publicBasePath +
      (pathname.startsWith('/') ? pathname : `/${pathname}`);
  }

  return `${pathname}${parsed.search}`;
}

app.prepare()
  .then(() => {
    const server = http.createServer((req, res) => {
      req.url = normalizeRequestUrl(req.url);
      handle(req, res);
    });

    server.listen(listenTarget, () => {
      console.log('Grougalorasalar frontend started');
    });
  })
  .catch((error) => {
    console.error('Frontend startup failed:', error);
    process.exit(1);
  });
