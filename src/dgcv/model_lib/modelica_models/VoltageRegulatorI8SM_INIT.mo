model VoltageRegulatorI8SM_INIT
  import Dynawo;
  
  Dynawo.Types.VoltageModulePu Efd0Pu (start = 1) "Initial voltage output in pu (base UNom)";
  Dynawo.Types.VoltageModulePu U0Pu (start = 1) "Initial stator voltage in pu (base UNom)";
  Dynawo.Types.VoltageModulePu URef0Pu "Initial control voltage in pu (base UNom)";

equation

  URef0Pu = U0Pu + Efd0Pu / 15;

end VoltageRegulatorI8SM_INIT;
