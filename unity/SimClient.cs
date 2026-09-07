// SimClient.cs — cliente Unity para server.py (patrón hw01 TC2008B).
// Uso: GameObject vacío -> agregar este script -> asignar voterPrefab y los Transforms.
// Corre `python3 server.py` antes de darle Play.
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;

[System.Serializable] public class Votante { public int id; public string estado; public string partido; public bool ine_valida; public bool prioridad; public int spawn_beat; }
[System.Serializable] public class Estacion { public int id; public int votante; }  // votante = 0 si null (JsonUtility)
[System.Serializable] public class Estado
{
    public int beat; public string hora; public bool running; public string clima;
    public int[] queue_ine, queue_ine_prio, queue_casilla, queue_casilla_prio;
    public Estacion[] recipientes, casillas;
    public Votante[] votantes;
}

public class SimClient : MonoBehaviour
{
    public string serverUrl = "http://localhost:6769";
    public int beatsPerRequest = 1;
    public float secondsPerBeat = 0.5f;
    public int nRecipientes = 3, nCasillas = 5, votersTarget = 450;

    [Header("Escena")]
    public GameObject voterPrefab;
    public Transform entrada, salida;
    public Transform filaIne, filaInePrio, filaCasilla, filaCasillaPrio;  // inicio de cada fila
    public Vector3 separacionFila = new Vector3(0, 0, -0.8f);
    public Transform[] recipientes;   // posiciones R1..Rn
    public Transform[] casillas;      // posiciones C1..Cn
    public float velocidad = 3f;

    Dictionary<int, GameObject> agentes = new Dictionary<int, GameObject>();
    Dictionary<int, Vector3> destinos = new Dictionary<int, Vector3>();
    Estado estado;

    IEnumerator Start()
    {
        string body = $"{{\"n_recipientes\":{nRecipientes},\"n_casillas\":{nCasillas},\"voters_target\":{votersTarget}}}";
        using (var req = new UnityWebRequest(serverUrl + "/init", "POST"))
        {
            req.uploadHandler = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(body));
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            yield return req.SendWebRequest();
            if (req.result != UnityWebRequest.Result.Success) { Debug.LogError(req.error); yield break; }
            Aplicar(req.downloadHandler.text);
        }
        while (estado == null || estado.running)
        {
            yield return new WaitForSeconds(secondsPerBeat);
            using (var req = UnityWebRequest.Get($"{serverUrl}/step?n={beatsPerRequest}"))
            {
                yield return req.SendWebRequest();
                if (req.result != UnityWebRequest.Result.Success) { Debug.LogError(req.error); yield break; }
                Aplicar(req.downloadHandler.text);
            }
        }
        Debug.Log("Simulación terminada. GET " + serverUrl + "/results");
    }

    void Aplicar(string json)
    {
        estado = JsonUtility.FromJson<Estado>(json);
        var idx = new Dictionary<string, int>();  // contador por fila para escalonar
        foreach (var v in estado.votantes)
        {
            if (!agentes.ContainsKey(v.id))
            {
                var go = Instantiate(voterPrefab, entrada.position, Quaternion.identity);
                go.name = $"Votante {v.id}";
                agentes[v.id] = go;
            }
            destinos[v.id] = Destino(v, idx);
        }
    }

    Vector3 Destino(Votante v, Dictionary<string, int> idx)
    {
        string e = v.estado;
        if (e.StartsWith("recipiente:")) return recipientes[int.Parse(e.Substring(11)) - 1].position;
        if (e.StartsWith("casilla:")) return casillas[int.Parse(e.Substring(8)) - 1].position;
        if (e == "salida" || e == "rechazado") return salida.position;
        Transform fila = e == "queue_ine" ? filaIne : e == "queue_ine_prio" ? filaInePrio
                       : e == "queue_casilla" ? filaCasilla : filaCasillaPrio;
        idx.TryGetValue(e, out int n); idx[e] = n + 1;
        return fila.position + separacionFila * n;
    }

    void Update()
    {
        foreach (var kv in destinos)
        {
            var t = agentes[kv.Key].transform;
            t.position = Vector3.MoveTowards(t.position, kv.Value, velocidad * Time.deltaTime);
        }
    }

    void OnGUI()
    {
        if (estado != null) GUI.Label(new Rect(10, 10, 400, 20), $"Beat {estado.beat} | {estado.hora} | {estado.clima} | fila INE: {estado.queue_ine.Length}");
    }
}
