// Forces https and the bare domain, then hands everything else to the static assets.
const CANONICAL_HOST = "shabpa.ir";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.protocol === "http:" || url.hostname !== CANONICAL_HOST) {
      url.protocol = "https:";
      url.hostname = CANONICAL_HOST;
      url.port = "";
      return Response.redirect(url.toString(), 301);
    }
    return env.ASSETS.fetch(request);
  },
};
