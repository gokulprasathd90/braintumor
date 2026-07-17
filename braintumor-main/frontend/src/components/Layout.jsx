/**
 * Layout — wraps every page with consistent max-width and padding.
 * Navbar is rendered once in App.jsx above all routes; Layout handles
 * the page content area only.
 */
export default function Layout({ children }) {
  return (
    <main className="min-h-screen bg-pipeline-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </div>
    </main>
  );
}
