import { redirect } from "next/navigation";

/**
 * The sidebar exposes a project-independent Studio entry point, while the
 * actual editor is scoped to a project at /studio/[projectId]. Send users to
 * the project picker instead of leaving them on a 404 page.
 */
export default function StudioIndexPage() {
  redirect("/projects");
}
