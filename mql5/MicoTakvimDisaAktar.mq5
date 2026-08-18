//+------------------------------------------------------------------+
//| MicoTakvimDisaAktar.mq5                                          |
//| Dumps the terminal's economic calendar to CSV so the Python side |
//| can read it. The calendar lives only in MQL5 - the Python API    |
//| has no equivalent - so this is the only way across.              |
//|                                                                  |
//| Times are written as the raw MT5 integer, which is the server's  |
//| wall clock encoded as a Unix epoch, the same frame as bar and    |
//| deal stamps. Do not convert here; the Python side reads it with  |
//| sessions.server_datetime and nothing shifts.                     |
//|                                                                  |
//| The first attempt asked for 900 days in one call and came back   |
//| 5401 (timeout): the terminal fetches calendar ranges from the    |
//| server on demand, and a wide first request outruns it. So the    |
//| range is walked in chunks, each retried, and a chunk that will   |
//| not come is reported rather than silently dropped.               |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input int    GerideGun   = 900;                    // how far back to dump
input string CikisDosya  = "micofx_takvim.csv";    // under MQL5\Files
input int    EnAzOnem    = 1;                      // 0=none 1=low 2=moderate 3=high
input int    ParcaGun    = 45;                     // days per request
input int    DenemeSayisi = 6;                     // retries per chunk
input int    BeklemeMs   = 700;                    // wait between retries

int          g_fh       = INVALID_HANDLE;
int          g_yazilan  = 0;
int          g_gorulen  = 0;
ulong        g_eklenen[];                          // value ids already written

//+------------------------------------------------------------------+
bool ZatenYazildi(const ulong id)
{
   int n = ArraySize(g_eklenen);
   for(int i = n - 1; i >= 0 && i > n - 4000; i--)   // recent window is enough
      if(g_eklenen[i] == id)
         return true;
   return false;
}

//+------------------------------------------------------------------+
void ParcayiYaz(const MqlCalendarValue &values[])
{
   for(int i = 0; i < ArraySize(values); i++)
   {
      g_gorulen++;
      if(ZatenYazildi(values[i].id))
         continue;

      MqlCalendarEvent olay;
      if(!CalendarEventById(values[i].event_id, olay))
         continue;
      if((int)olay.importance < EnAzOnem)
         continue;

      MqlCalendarCountry ulke;
      string kur = "";
      if(CalendarCountryById(olay.country_id, ulke))
         kur = ulke.currency;

      // has_value flags: an unreleased figure must read empty, not zero.
      string gercek = (values[i].HasActualValue())   ? DoubleToString(values[i].GetActualValue(), 6)   : "";
      string beklen = (values[i].HasForecastValue()) ? DoubleToString(values[i].GetForecastValue(), 6) : "";
      string onceki = (values[i].HasPreviousValue()) ? DoubleToString(values[i].GetPreviousValue(), 6) : "";

      FileWrite(g_fh,
                (long)values[i].time, kur, (int)olay.importance, (long)olay.id,
                olay.name, EnumToString(olay.sector),
                gercek, beklen, onceki, olay.unit);

      int n = ArraySize(g_eklenen);
      ArrayResize(g_eklenen, n + 1);
      g_eklenen[n] = values[i].id;
      g_yazilan++;
   }
}

//+------------------------------------------------------------------+
void OnStart()
{
   g_fh = FileOpen(CikisDosya, FILE_WRITE | FILE_CSV | FILE_ANSI, ';');
   if(g_fh == INVALID_HANDLE)
   {
      PrintFormat("MicoTakvim: dosya acilamadi %s hata %d", CikisDosya, GetLastError());
      return;
   }
   FileWrite(g_fh, "time", "currency", "importance", "event_id", "event",
             "sector", "actual", "forecast", "previous", "unit");

   datetime bitis  = TimeCurrent() + 30 * 24 * 60 * 60;
   datetime baslar = TimeCurrent() - (datetime)GerideGun * 24 * 60 * 60;
   int      adim   = MathMax(1, ParcaGun) * 24 * 60 * 60;
   int      parca = 0, bosParca = 0, hataliParca = 0;

   for(datetime p0 = baslar; p0 < bitis; p0 += adim)
   {
      datetime p1 = (datetime)MathMin((long)bitis, (long)p0 + adim);
      parca++;

      MqlCalendarValue values[];
      int n = -1;
      for(int deneme = 0; deneme < MathMax(1, DenemeSayisi); deneme++)
      {
         ResetLastError();
         n = CalendarValueHistory(values, p0, p1, NULL, NULL);
         if(n > 0)
            break;
         int hata = GetLastError();
         // 5401 is a timeout while the terminal fetches the range. Waiting and
         // asking again is the documented remedy; an empty stretch (holidays,
         // pre-history) returns 0 with no error and must not spin.
         if(hata == 0 || n == 0)
            break;
         Sleep(MathMax(50, BeklemeMs));
      }

      if(n > 0)
         ParcayiYaz(values);
      else if(GetLastError() != 0)
      {
         hataliParca++;
         PrintFormat("MicoTakvim: parca %s..%s alinamadi (hata %d)",
                     TimeToString(p0, TIME_DATE), TimeToString(p1, TIME_DATE), GetLastError());
      }
      else
         bosParca++;
   }

   FileClose(g_fh);
   PrintFormat("MicoTakvim: %d parca | %d kayit gorildi | %d yazildi | bos %d | hatali %d -> MQL5\Files\%s",
               parca, g_gorulen, g_yazilan, bosParca, hataliParca, CikisDosya);
   if(g_yazilan == 0)
      Print("MicoTakvim: hic kayit yok. Araclar > Secenekler > Sunucu > 'Haberleri etkinlestir' "
            "acik olmali ve Arac Kutusu > Takvim sekmesi bir kez acilmali.");
}
//+------------------------------------------------------------------+
