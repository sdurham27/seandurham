import { useEffect, useState } from "react";
import { fetchLibraryStatus, LibraryStatus } from "../lib/api";

export function useLibraryStatus() {
  const [status, setStatus] = useState<LibraryStatus | null>(null);

  useEffect(() => {
    fetchLibraryStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  return status;
}
