import createMiddleware from "next-intl/middleware";

import { routing } from "./i18n/routing";

// Redirects "/" to the visitor's language ("/ko", "/zh-TW" or "/en") based on
// Accept-Language, and remembers a manual switch in a cookie.
export default createMiddleware(routing);

export const config = {
  // Everything except API routes, Next internals and files with an extension.
  matcher: "/((?!api|_next|_vercel|.*\\..*).*)",
};
