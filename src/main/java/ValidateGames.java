import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import java.nio.file.Files;
import java.nio.file.Paths;

public class ValidateGames {

    private static final int THREADS = 8;
    private static final int MAX_REQUESTS_PER_SECOND = 5;
    private static final long MIN_INTERVAL_MS = 1000 / MAX_REQUESTS_PER_SECOND;
    public static final String json_filename = "oct_dec_game_ids.json";

    private static final AtomicLong lastRequestTime = new AtomicLong(0);
    private static final HttpClient client = HttpClient.newHttpClient();

    // Debug classification
    private static final Map<String, List<Integer>> debugMap = new ConcurrentHashMap<>();

    // ✅ Valid IDs output
    private static final List<Integer> validGameIds = Collections.synchronizedList(new ArrayList<>());

    private static synchronized void rateLimit() {
        long now = System.currentTimeMillis();
        long elapsed = now - lastRequestTime.get();
        if (elapsed < MIN_INTERVAL_MS) {
            try {
                Thread.sleep(MIN_INTERVAL_MS - elapsed);
            } catch (InterruptedException ignored) {
            }
        }
        lastRequestTime.set(System.currentTimeMillis());
    }

    private static void addToDebugMap(String key, int gameId) {
        debugMap
                .computeIfAbsent(key, k -> Collections.synchronizedList(new ArrayList<>()))
                .add(gameId);
    }

    private static boolean validateGame(int gameId) {
        try {
            rateLimit();

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create("https://ncaa-api.henrygd.me/game/" + gameId))
                    .timeout(Duration.ofSeconds(10))
                    .GET()
                    .build();

            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                addToDebugMap("HTTP_ERROR", gameId);
                return false;
            }

            String body = response.body();

            boolean isWSO = body.contains("\"sportCode\":\"WSO\"");
            boolean isMSO = body.contains("\"sportCode\":\"MSO\"");
            boolean isD3 = body.contains("\"division\":3");

            if (isWSO && isD3) {
                addToDebugMap("WSO_d3", gameId);
                validGameIds.add(gameId);
                return true;
            }

            if (isWSO) {
                addToDebugMap("WSO_other", gameId);
            } else if (isMSO) {
                addToDebugMap("MSO", gameId);
            } else {
                addToDebugMap("OTHER", gameId);
            }

            return false;

        } catch (Exception e) {
            addToDebugMap("EXCEPTION", gameId);
            return false;
        }
    }

    private static List<Integer> loadGameIds(String filename) throws Exception {
        String content = new String(Files.readAllBytes(Paths.get(filename)));
        content = content.replace("[", "").replace("]", "").trim();

        if (content.isEmpty()) {
            return Collections.emptyList();
        }

        String[] parts = content.split(",");
        List<Integer> ids = new ArrayList<>();

        for (String p : parts) {
            ids.add(Integer.parseInt(p.trim()));
        }

        return ids;
    }

    public static void main(String[] args) throws Exception {

        List<Integer> gameIds = loadGameIds(json_filename);
        System.out.println("Loaded " + gameIds.size() + " game IDs");

        ExecutorService executor = Executors.newFixedThreadPool(THREADS);
        CompletionService<Integer> cs = new ExecutorCompletionService<>(executor);

        for (int gameId : gameIds) {
            cs.submit(() -> validateGame(gameId) ? gameId : null);
        }

        executor.shutdown();
        executor.awaitTermination(30, TimeUnit.MINUTES);

        System.out.println("\nValid D3 Women's Soccer Games:");
        for (int i = 0; i < gameIds.size(); i++) {
            Integer result = cs.take().get();
            if (result != null) {
                System.out.println("✔ " + result);
            }
        }

        System.out.println("\n===== DEBUG MAP =====");
        for (Map.Entry<String, List<Integer>> e : debugMap.entrySet()) {
            System.out.println(
                    e.getKey() + " (" + e.getValue().size() + "): " + e.getValue());
        }

        // ----------------------------
        // WRITE OUTPUT FILE
        // ----------------------------
        Collections.sort(validGameIds);

        Files.write(
                Paths.get("validated_aug_sept_game_ids.json"),
                validGameIds.toString().getBytes());

        System.out.println(
                "\nWrote " + validGameIds.size()
                        + " validated game IDs to validated_aug_sept_game_ids.json");
    }
}
